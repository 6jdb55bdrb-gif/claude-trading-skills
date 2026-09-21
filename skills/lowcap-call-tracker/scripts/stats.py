#!/usr/bin/env python3
"""Statistics over the call database: printed after every run and saved to stats.md.

Outcome classification (as configured by the closing rule):

* ``RIGHT``   — expired above the entry, or open and currently up
* ``WRONG``   — expired at or below the entry (or stopped out, when a
  ``close_threshold_pct`` is configured)
* ``NEUTRAL`` — still open and not up: the contract still has time

Shadow calls (Judge said SKIP) are tracked with the same machinery as active
calls, so "is the Judge adding value?" is answerable from the same table.

CLI:
    python3 stats.py --db state/lowcap_calls.db
    python3 stats.py --write     # also refresh reports/lowcap-tracker/stats.md
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from call_db import KIND_ACTIVE, KIND_SHADOW, STATUS_EXPIRED, STATUS_OPEN, CallDatabase

from config import load_config, resolve_path

ROLES = ("researcher", "technician", "skeptic", "risk_manager")
ROLE_SCORE_COLUMN = {
    "researcher": "researcher_score",
    "technician": "technician_score",
    "skeptic": "skeptic_score",
    "risk_manager": "risk_manager_score",
}


def outcome(row: sqlite3.Row | dict[str, Any]) -> str:
    """RIGHT / WRONG / NEUTRAL for one call.

    A call is an option that runs to expiry, so a closed call is judged on where
    it finished: expired above the entry is RIGHT, at or below it is WRONG. An
    open call is RIGHT while it is up and NEUTRAL otherwise — it still has time.
    A legacy stop-out (only when a threshold is configured) stays WRONG.
    """
    pnl = row["pnl_pct"]
    status = row["status"]
    if status == STATUS_EXPIRED:
        return "RIGHT" if (pnl is not None and pnl > 0) else "WRONG"
    if status != STATUS_OPEN:
        return "WRONG"
    if pnl is not None and pnl > 0:
        return "RIGHT"
    return "NEUTRAL"


def _pnls(rows: Sequence[Any]) -> list[float]:
    return [float(row["pnl_pct"]) for row in rows if row["pnl_pct"] is not None]


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation without pulling in a numeric dependency."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mean_x, mean_y = mean(xs), mean(ys)
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    denom_x = sum(value * value for value in dx) ** 0.5
    denom_y = sum(value * value for value in dy) ** 0.5
    if denom_x == 0 or denom_y == 0:
        return None
    return round(sum(a * b for a, b in zip(dx, dy)) / (denom_x * denom_y), 3)


def _group_block(rows: Sequence[Any]) -> dict[str, Any]:
    outcomes = [outcome(row) for row in rows]
    pnls = _pnls(rows)
    total = len(rows)
    right = outcomes.count("RIGHT")
    wrong = outcomes.count("WRONG")
    neutral = outcomes.count("NEUTRAL")
    return {
        "total": total,
        "open": sum(1 for row in rows if row["status"] == STATUS_OPEN),
        "right": right,
        "wrong": wrong,
        "neutral": neutral,
        "hit_rate_pct": round(right / total * 100, 1) if total else None,
        "avg_pnl_pct": round(mean(pnls), 2) if pnls else None,
    }


def _by(rows: Sequence[Any], key: str) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[Any]] = {}
    for row in rows:
        buckets.setdefault(str(row[key] or "unknown"), []).append(row)
    return {name: _group_block(group) for name, group in sorted(buckets.items())}


def _extreme(rows: Sequence[Any], *, worst: bool = False) -> dict[str, Any] | None:
    scored = [row for row in rows if row["pnl_pct"] is not None]
    if not scored:
        return None
    row = (
        min(scored, key=lambda r: r["pnl_pct"])
        if worst
        else max(scored, key=lambda r: r["pnl_pct"])
    )
    return {
        "ticker": row["ticker"],
        "direction": row["direction"],
        "variant": row["screen_variant"],
        "kind": row["kind"],
        "pnl_pct": round(float(row["pnl_pct"]), 2),
        "entry_price": row["entry_price"],
        "current_price": row["current_price"],
        "call_date": row["call_date"],
    }


def _role_block(rows: Sequence[Any]) -> dict[str, Any]:
    """Per-role predictive power: winners' average score vs. everyone else's."""
    out: dict[str, Any] = {}
    winners = [row for row in rows if outcome(row) == "RIGHT"]
    losers = [row for row in rows if outcome(row) != "RIGHT"]
    for role, column in ROLE_SCORE_COLUMN.items():
        winner_scores = [float(row[column]) for row in winners if row[column] is not None]
        loser_scores = [float(row[column]) for row in losers if row[column] is not None]
        paired = [
            (float(row[column]), float(row["pnl_pct"]))
            for row in rows
            if row[column] is not None and row["pnl_pct"] is not None
        ]
        out[role] = {
            "avg_score_winners": round(mean(winner_scores), 2) if winner_scores else None,
            "avg_score_others": round(mean(loser_scores), 2) if loser_scores else None,
            "edge": (
                round(mean(winner_scores) - mean(loser_scores), 2)
                if winner_scores and loser_scores
                else None
            ),
            "corr_score_vs_pnl": _pearson([p[0] for p in paired], [p[1] for p in paired]),
            "samples": len(paired),
            "polarity": "severity (lower is better)"
            if role == "skeptic"
            else "quality (higher is better)",
        }
    return out


def _confidence_blocks(rows: Sequence[Any], buckets: Iterable[Sequence[int]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for bucket in buckets:
        low, high = int(bucket[0]), int(bucket[1])
        selected = [
            row
            for row in rows
            if row["confidence"] is not None and low <= int(row["confidence"]) < high
        ] + (
            [row for row in rows if row["confidence"] is not None and int(row["confidence"]) == 100]
            if high == 100
            else []
        )
        out[f"{low}-{high}"] = _group_block(selected)
    return out


def compute_stats(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    rows = db.all_calls()
    active = [row for row in rows if row["kind"] == KIND_ACTIVE]
    shadow = [row for row in rows if row["kind"] == KIND_SHADOW]
    take_pnls = _pnls(active)
    shadow_pnls = _pnls(shadow)

    overall = _group_block(rows)
    overall.update(
        {
            "take_calls": len(active),
            "shadow_calls": len(shadow),
            "best_call": _extreme(rows),
            "worst_call": _extreme(rows, worst=True),
        }
    )

    judge_edge = None
    if take_pnls and shadow_pnls:
        judge_edge = round(mean(take_pnls) - mean(shadow_pnls), 2)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "close_threshold_pct": config["tracker"].get("close_threshold_pct"),
        "close_rule": (
            "contracts run to expiry"
            + (
                ""
                if config["tracker"].get("close_threshold_pct") is None
                else f", or an early stop-out at {config['tracker']['close_threshold_pct']}%"
            )
        ),
        "overall": overall,
        "portfolio": {
            "equal_weight_pnl_pct_take_only": round(mean(take_pnls), 2) if take_pnls else None,
            "equal_weight_pnl_pct_all_calls": (
                round(mean(_pnls(rows)), 2) if _pnls(rows) else None
            ),
            "take_calls_counted": len(take_pnls),
        },
        "by_instrument": _by(rows, "instrument"),
        "by_direction": _by(rows, "direction"),
        "by_asset_type": _by(rows, "asset_type"),
        "by_variant": _by(rows, "screen_variant"),
        "take_vs_skip": {
            "take": _group_block(active),
            "skip_shadow": _group_block(shadow),
            "judge_edge_avg_pnl_pct": judge_edge,
            "verdict": (
                "no comparison yet"
                if judge_edge is None
                else "no separation yet"
                if abs(judge_edge) < 0.5
                else "Judge is adding value"
                if judge_edge > 0
                else "Judge is not adding value"
            ),
        },
        "role_accuracy": _role_block(rows),
        "confidence_buckets": _confidence_blocks(
            rows, config["learning"].get("confidence_buckets", [[0, 40], [40, 70], [70, 100]])
        ),
        "recent_runs": [
            {
                "run_id": run["run_id"],
                "started_at": run["started_at"],
                "screening_ran": bool(run["screening_ran"]),
                "new_calls": run["new_calls"],
                "closed": run["closed"],
                "llm_cost_usd": run["llm_cost_usd"],
            }
            for run in db.runs(limit=5)
        ],
    }


def _row(cells: Sequence[Any]) -> str:
    return "| " + " | ".join("—" if cell is None else str(cell) for cell in cells) + " |"


def _group_table(title: str, groups: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        f"### {title}",
        "",
        _row(["Group", "Calls", "Open", "Right", "Wrong", "Neutral", "Hit rate %", "Avg PnL %"]),
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, block in groups.items():
        lines.append(
            _row(
                [
                    name,
                    block["total"],
                    block["open"],
                    block["right"],
                    block["wrong"],
                    block["neutral"],
                    block["hit_rate_pct"],
                    block["avg_pnl_pct"],
                ]
            )
        )
    lines.append("")
    return lines


def render_markdown(stats: dict[str, Any]) -> str:
    overall = stats["overall"]
    lines = [
        "# Lowcap Call Tracker — Statistics",
        "",
        f"**Generated:** {stats['generated_at']}  ",
        f"**Close rule:** {stats['close_rule']}",
        "",
        "## Overall",
        "",
        _row(["Metric", "Value"]),
        "|---|---|",
        _row(["Total calls", overall["total"]]),
        _row(["TAKE calls", overall["take_calls"]]),
        _row(["Shadow (SKIP) calls", overall["shadow_calls"]]),
        _row(["Open", overall["open"]]),
        _row(["Right", overall["right"]]),
        _row(["Wrong", overall["wrong"]]),
        _row(["Neutral", overall["neutral"]]),
        _row(["Hit rate %", overall["hit_rate_pct"]]),
        _row(["Average PnL % per call", overall["avg_pnl_pct"]]),
        _row(
            [
                "Portfolio PnL % (equal weight, TAKE only)",
                stats["portfolio"]["equal_weight_pnl_pct_take_only"],
            ]
        ),
        "",
    ]
    for label, key in (("Best call", "best_call"), ("Worst call", "worst_call")):
        call = overall.get(key)
        if call:
            lines.append(
                f"**{label}:** {call['ticker']} ({call['direction']}, {call['variant']}, "
                f"{call['kind']}) {call['pnl_pct']:+.2f}% "
                f"— entry {call['entry_price']} → {call['current_price']}"
            )
    lines.append("")

    lines += _group_table("By instrument (call / put)", stats["by_instrument"])
    lines += _group_table("By asset type", stats["by_asset_type"])
    lines += _group_table("By screen variant", stats["by_variant"])
    lines += _group_table(
        "TAKE vs SKIP (is the Judge adding value?)",
        {
            "TAKE": stats["take_vs_skip"]["take"],
            "SKIP (shadow)": stats["take_vs_skip"]["skip_shadow"],
        },
    )
    lines += [
        f"**Judge edge (avg PnL TAKE − avg PnL shadow):** "
        f"{stats['take_vs_skip']['judge_edge_avg_pnl_pct']} → {stats['take_vs_skip']['verdict']}",
        "",
        "### Per-role accuracy",
        "",
        _row(
            [
                "Role",
                "Avg score (winners)",
                "Avg score (others)",
                "Edge",
                "Corr(score, PnL)",
                "n",
                "Polarity",
            ]
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for role in ROLES:
        block = stats["role_accuracy"][role]
        lines.append(
            _row(
                [
                    role,
                    block["avg_score_winners"],
                    block["avg_score_others"],
                    block["edge"],
                    block["corr_score_vs_pnl"],
                    block["samples"],
                    block["polarity"],
                ]
            )
        )
    lines += ["", "### Confidence buckets", ""]
    lines += _group_table("Judge confidence", stats["confidence_buckets"])[1:]
    if stats["recent_runs"]:
        lines += [
            "### Recent runs",
            "",
            _row(["Run", "Started", "Screened", "New calls", "Closed", "LLM $"]),
            "|---|---|---|---|---|---|",
        ]
        for run in stats["recent_runs"]:
            lines.append(
                _row(
                    [
                        run["run_id"],
                        run["started_at"],
                        "yes" if run["screening_ran"] else "no",
                        run["new_calls"],
                        run["closed"],
                        run["llm_cost_usd"],
                    ]
                )
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_text(stats: dict[str, Any]) -> str:
    overall = stats["overall"]
    take = stats["take_vs_skip"]
    lines = [
        "=" * 72,
        "CALL STATISTICS",
        "=" * 72,
        f"  total={overall['total']}  open={overall['open']}  right={overall['right']}  "
        f"wrong={overall['wrong']}  neutral={overall['neutral']}  "
        f"hit_rate={overall['hit_rate_pct']}%",
        f"  avg PnL/call={overall['avg_pnl_pct']}%   "
        f"portfolio (equal weight, TAKE only)={stats['portfolio']['equal_weight_pnl_pct_take_only']}%",
    ]
    for label, key in (("best", "best_call"), ("worst", "worst_call")):
        call = overall.get(key)
        if call:
            lines.append(f"  {label}: {call['ticker']} {call['pnl_pct']:+.2f}% ({call['variant']})")
    lines.append(
        f"  TAKE n={take['take']['total']} avg={take['take']['avg_pnl_pct']}%  "
        f"SKIP n={take['skip_shadow']['total']} avg={take['skip_shadow']['avg_pnl_pct']}%  "
        f"edge={take['judge_edge_avg_pnl_pct']} ({take['verdict']})"
    )
    for title, key in (
        ("instrument", "by_instrument"),
        ("asset type", "by_asset_type"),
        ("variant", "by_variant"),
        ("confidence", "confidence_buckets"),
    ):
        parts = [
            f"{name}: n={block['total']} hit={block['hit_rate_pct']}% avg={block['avg_pnl_pct']}%"
            for name, block in stats[key].items()
        ]
        lines.append(f"  by {title}: " + " | ".join(parts) if parts else f"  by {title}: —")
    for role in ROLES:
        block = stats["role_accuracy"][role]
        lines.append(
            f"  role {role:<13} winners={block['avg_score_winners']} others={block['avg_score_others']} "
            f"edge={block['edge']} corr={block['corr_score_vs_pnl']} (n={block['samples']})"
        )
    return "\n".join(lines)


def write_stats_file(stats: dict[str, Any], config: dict[str, Any]) -> str:
    path = resolve_path(config, "stats_file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(stats), encoding="utf-8")
    return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lowcap call statistics")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--write", action="store_true", help="Also write stats.md")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    with CallDatabase(args.db or resolve_path(config, "db_path")) as db:
        stats = compute_stats(db, config)
    if args.json:
        print(json.dumps(stats, indent=2, default=str))
    else:
        print(render_text(stats))
    if args.write:
        print(f"\nstats.md: {write_stats_file(stats, config)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
