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

from call_db import (
    KIND_ACTIVE,
    KIND_SHADOW,
    KIND_UNREVIEWED,
    STATUS_EXPIRED,
    STATUS_OPEN,
    CallDatabase,
)

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


def _backend_block(
    health: dict[str, Any] | None,
    reviewed: list[Any],
    unreviewed: list[Any],
    active: list[Any],
    shadow: list[Any],
) -> dict[str, Any]:
    """The one-line health summary that leads stats.md."""
    judged = len(active) + len(shadow)
    ratio = f"{len(active)}/{len(shadow)}" if judged else "0/0"
    take_pct = round(len(active) / judged * 100, 1) if judged else None
    status = "UNKNOWN"
    if health is not None:
        status = "UP" if health.get("ok") else "DOWN"
    return {
        "status": status,
        "reason": (health or {}).get("reason"),
        "model": (health or {}).get("model"),
        "latency_ms": (health or {}).get("latency_ms"),
        "reviewed_calls": len(reviewed),
        "unreviewed_calls": len(unreviewed),
        "take_skip_ratio": ratio,
        "take_pct_of_reviewed": take_pct,
    }


def compute_stats(
    db: CallDatabase, config: dict[str, Any], *, backend_health: dict[str, Any] | None = None
) -> dict[str, Any]:
    rows = db.all_calls()
    active = [row for row in rows if row["kind"] == KIND_ACTIVE]
    shadow = [row for row in rows if row["kind"] == KIND_SHADOW]
    # An UNREVIEWED call is a screener record with no opinion attached. It counts
    # toward what the screener found and how those names moved, and it is kept
    # out of every statistic that judges the Judge — otherwise a stretch of
    # backend downtime would read as a stretch of terrible decisions.
    unreviewed = [row for row in rows if row["kind"] == KIND_UNREVIEWED]
    reviewed = [row for row in rows if row["kind"] != KIND_UNREVIEWED]
    take_pnls = _pnls(active)
    shadow_pnls = _pnls(shadow)
    all_pnls = _pnls(rows)

    overall = _group_block(rows)
    overall.update(
        {
            "take_calls": len(active),
            "shadow_calls": len(shadow),
            "unreviewed_calls": len(unreviewed),
            "reviewed_calls": len(reviewed),
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
            # The headline: equal money into every call the tracker has made,
            # judged or not, long or short. This is "where would I be if I had
            # taken all of them", which is the only number that needs no
            # explanation before it can be acted on.
            "total_pnl_pct": round(mean(all_pnls), 2) if all_pnls else None,
            "calls_counted": len(all_pnls),
            "equal_weight_pnl_pct_take_only": round(mean(take_pnls), 2) if take_pnls else None,
            "equal_weight_pnl_pct_all_calls": round(mean(all_pnls), 2) if all_pnls else None,
            "take_calls_counted": len(take_pnls),
        },
        # An unjudged call chose no instrument, so it belongs in no bucket.
        "by_instrument": _by([row for row in rows if row["instrument"]], "instrument"),
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
        # Reviewed rows only: an unjudged call has no scores and no confidence.
        "role_accuracy": _role_block(reviewed),
        "confidence_buckets": _confidence_blocks(
            reviewed, config["learning"].get("confidence_buckets", [[0, 40], [40, 70], [70, 100]])
        ),
        "backend": _backend_block(backend_health, reviewed, unreviewed, active, shadow),
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


def format_backend_line(backend: dict[str, Any]) -> str:
    """The status line that leads every statistics file."""
    ratio = backend.get("take_skip_ratio", "0/0")
    reviewed = backend.get("reviewed_calls", 0)
    unreviewed = backend.get("unreviewed_calls", 0)
    share = backend.get("take_pct_of_reviewed")
    share_text = f" ({share}% TAKE)" if share is not None else ""
    return (
        f"**Backend:** {backend.get('status', 'UNKNOWN')} · "
        f"reviewed {reviewed} / unreviewed {unreviewed} · "
        f"TAKE/SKIP {ratio}{share_text}"
    )


def render_markdown(stats: dict[str, Any]) -> str:
    overall = stats["overall"]
    backend = stats.get("backend") or {}
    lines = ["# Lowcap Call Tracker — Statistics", ""]
    if backend.get("status") == "DOWN":
        # Loud and first: every number below was produced without a working
        # role backend, and new hits are being recorded UNREVIEWED.
        lines += [
            "> ## ⛔ BACKEND DOWN",
            ">",
            f"> The role review could not run: {backend.get('reason', 'unknown reason')}.",
            "> New screener hits are recorded UNREVIEWED and will be judged on the",
            "> next healthy run. No decision below was made while the backend was down.",
            "",
        ]
    lines += [
        format_backend_line(backend),
        "",
        f"**Total PnL:** {_signed(stats['portfolio']['total_pnl_pct'])} "
        f"— equal weight across all {stats['portfolio']['calls_counted']} priced call(s)",
        "",
        f"**Generated:** {stats['generated_at']}  ",
        f"**Close rule:** {stats['close_rule']}",
        "",
        "## Overall",
        "",
        _row(["Metric", "Value"]),
        "|---|---|",
        _row(["Total calls", overall["total"]]),
        _row(["Reviewed calls", overall.get("reviewed_calls")]),
        _row(["UNREVIEWED calls", overall.get("unreviewed_calls")]),
        _row(["TAKE calls", overall["take_calls"]]),
        _row(["Shadow (SKIP) calls", overall["shadow_calls"]]),
        _row(["Open", overall["open"]]),
        _row(["Right", overall["right"]]),
        _row(["Wrong", overall["wrong"]]),
        _row(["Neutral", overall["neutral"]]),
        _row(["Hit rate %", overall["hit_rate_pct"]]),
        _row(
            [
                "**Total PnL % (equal weight, all calls)**",
                _signed(stats["portfolio"]["total_pnl_pct"]),
            ]
        ),
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


def _signed(value: Any) -> str:
    """A percentage with an explicit sign: +3.03%, -10.80%, or an em dash."""
    return "—" if value is None else f"{value:+.2f}%"


def _dash(value: Any) -> str:
    """Any value, with an em dash for nothing."""
    return "—" if value is None else str(value)


def _pct(value: Any) -> str:
    """A percentage, or an em dash. 'None%' is not a statistic."""
    return "—" if value is None else f"{value}%"


def render_text(stats: dict[str, Any]) -> str:
    overall = stats["overall"]
    take = stats["take_vs_skip"]
    backend = stats.get("backend") or {}
    lines = [
        "=" * 72,
        "CALL STATISTICS",
        "=" * 72,
        f"  backend={backend.get('status', 'UNKNOWN')}  "
        f"reviewed={backend.get('reviewed_calls', 0)}  "
        f"unreviewed={backend.get('unreviewed_calls', 0)}  "
        f"TAKE/SKIP={backend.get('take_skip_ratio', '0/0')}",
        f"  total={overall['total']}  open={overall['open']}  right={overall['right']}  "
        f"wrong={overall['wrong']}  neutral={overall['neutral']}  "
        f"hit_rate={_pct(overall['hit_rate_pct'])}",
        f"  TOTAL PnL (equal weight, all {stats['portfolio']['calls_counted']} calls)="
        f"{_signed(stats['portfolio']['total_pnl_pct'])}",
        f"  avg PnL/call={_pct(overall['avg_pnl_pct'])}   "
        "portfolio (equal weight, TAKE only)="
        f"{_pct(stats['portfolio']['equal_weight_pnl_pct_take_only'])}",
    ]
    for label, key in (("best", "best_call"), ("worst", "worst_call")):
        call = overall.get(key)
        if call:
            lines.append(f"  {label}: {call['ticker']} {call['pnl_pct']:+.2f}% ({call['variant']})")
    lines.append(
        f"  TAKE n={take['take']['total']} avg={_pct(take['take']['avg_pnl_pct'])}  "
        f"SKIP n={take['skip_shadow']['total']} avg={_pct(take['skip_shadow']['avg_pnl_pct'])}  "
        f"edge={_dash(take['judge_edge_avg_pnl_pct'])} ({take['verdict']})"
    )
    for title, key in (
        ("instrument", "by_instrument"),
        ("asset type", "by_asset_type"),
        ("variant", "by_variant"),
        ("confidence", "confidence_buckets"),
    ):
        parts = [
            f"{name}: n={block['total']} hit={_pct(block['hit_rate_pct'])} "
            f"avg={_pct(block['avg_pnl_pct'])}"
            for name, block in stats[key].items()
        ]
        lines.append(f"  by {title}: " + " | ".join(parts) if parts else f"  by {title}: —")
    for role in ROLES:
        block = stats["role_accuracy"][role]
        lines.append(
            f"  role {role:<13} winners={_dash(block['avg_score_winners'])} "
            f"others={_dash(block['avg_score_others'])} edge={_dash(block['edge'])} "
            f"corr={_dash(block['corr_score_vs_pnl'])} (n={block['samples']})"
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
