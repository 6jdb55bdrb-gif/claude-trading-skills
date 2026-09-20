#!/usr/bin/env python3
"""Weekly learning loop: analyse resolved calls and PROPOSE changes.

Nothing is applied automatically. The loop writes ``improvements.md`` with
concrete, reviewable proposals for three levers:

1. Role prompts (``agents/lowcap-*.md``) — where a role's score does not predict
   outcomes.
2. Screener filters (``screener.variants`` in the config) — where a variant
   under-performs.
3. Judge weighting / confidence floor (``roles.weights``, ``roles.judge``) —
   where the Judge's selectivity or calibration is off.

CLI:
    python3 learning_loop.py --write
    python3 learning_loop.py --if-due      # only when 7+ days since last write
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from call_db import CallDatabase
from stats import ROLES, compute_stats

from config import load_config, resolve_path


def _fmt(value: Any, suffix: str = "") -> str:
    return "—" if value is None else f"{value}{suffix}"


def analyse(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    """Build the proposal set from the call history."""
    stats = compute_stats(db, config)
    learning = config["learning"]
    min_samples = int(learning.get("min_samples", 10))
    lookback_days = int(learning.get("lookback_days", 90))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

    rows = [row for row in db.all_calls() if str(row["call_date"]) >= cutoff]
    resolved = [row for row in rows if row["pnl_pct"] is not None]
    proposals: list[dict[str, Any]] = []

    # --- 1. Role predictive power -----------------------------------------
    for role in ROLES:
        block = stats["role_accuracy"][role]
        samples = block["samples"] or 0
        edge = block["edge"]
        corr = block["corr_score_vs_pnl"]
        if samples < min_samples:
            continue
        expect_negative = role == "skeptic"  # severity: lower should be better
        useful = (
            (corr is not None and corr < -0.1)
            if expect_negative
            else (corr is not None and corr > 0.1)
        )
        if useful:
            continue
        proposals.append(
            {
                "target": f"agents/lowcap-{role.replace('_', '-')}.md",
                "lever": "role prompt",
                "severity": "medium",
                "finding": (
                    f"{role} score does not separate winners from losers "
                    f"(edge {_fmt(edge)}, corr {_fmt(corr)} over {samples} calls; "
                    f"{'negative' if expect_negative else 'positive'} correlation expected)"
                ),
                "proposal": (
                    f"Tighten the {role} scoring rubric: add a worked example for the "
                    f"3-6 band, and require the score to cite a specific field "
                    f"(catalyst date, extension %, dollar volume) rather than a judgement word."
                ),
            }
        )

    # --- 2. Variant performance -------------------------------------------
    for variant, block in stats["by_variant"].items():
        if (block["total"] or 0) < max(3, min_samples // 2):
            continue
        if (block["avg_pnl_pct"] or 0) >= 0 and (block["hit_rate_pct"] or 0) >= 40:
            continue
        proposals.append(
            {
                "target": f"screener.variants.{variant}.filters",
                "lever": "screener filters",
                "severity": "high" if (block["avg_pnl_pct"] or 0) < -10 else "medium",
                "finding": (
                    f"variant '{variant}': {block['total']} calls, hit rate "
                    f"{_fmt(block['hit_rate_pct'], '%')}, avg PnL {_fmt(block['avg_pnl_pct'], '%')}"
                ),
                "proposal": _variant_proposal(variant, config),
            }
        )

    # --- 3. Judge weighting and calibration -------------------------------
    take_vs_skip = stats["take_vs_skip"]
    edge = take_vs_skip["judge_edge_avg_pnl_pct"]
    if (
        take_vs_skip["take"]["total"] >= min_samples
        and take_vs_skip["skip_shadow"]["total"] >= 3
        and edge is not None
        and edge <= 0
    ):
        proposals.append(
            {
                "target": "roles.weights / roles.judge.min_confidence_to_take",
                "lever": "judge weighting",
                "severity": "high",
                "finding": (
                    f"shadow calls outperform TAKE calls by {abs(edge):.2f} pp "
                    f"(TAKE avg {_fmt(take_vs_skip['take']['avg_pnl_pct'], '%')} vs shadow "
                    f"{_fmt(take_vs_skip['skip_shadow']['avg_pnl_pct'], '%')}): the Judge is "
                    "filtering out the wrong calls"
                ),
                "proposal": (
                    "Re-weight the blend toward whichever role shows the strongest "
                    "correlation in the table above, and review the SKIPs with the highest "
                    "PnL for the objection that was over-weighted."
                ),
            }
        )

    buckets = stats["confidence_buckets"]
    ordered = [(name, block) for name, block in buckets.items() if (block["total"] or 0) >= 3]
    for (low_name, low_block), (high_name, high_block) in zip(ordered, ordered[1:]):
        if (low_block["hit_rate_pct"] or 0) > (high_block["hit_rate_pct"] or 0):
            proposals.append(
                {
                    "target": "roles.judge (confidence calibration)",
                    "lever": "judge weighting",
                    "severity": "medium",
                    "finding": (
                        f"confidence bucket {low_name} hits "
                        f"{_fmt(low_block['hit_rate_pct'], '%')} while {high_name} hits "
                        f"{_fmt(high_block['hit_rate_pct'], '%')}: confidence is inverted"
                    ),
                    "proposal": (
                        "Add the calibration table from the observed buckets to the Judge "
                        "prompt, and state explicitly which combinations may exceed 80."
                    ),
                }
            )

    if not resolved:
        proposals.append(
            {
                "target": "(none)",
                "lever": "data",
                "severity": "info",
                "finding": "no priced calls in the lookback window",
                "proposal": "Let the tracker run; revisit after the first full week of calls.",
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lookback_days": lookback_days,
        "min_samples": min_samples,
        "calls_in_window": len(rows),
        "resolved_in_window": len(resolved),
        "stats": stats,
        "proposals": proposals,
    }


def _variant_proposal(variant: str, config: dict[str, Any]) -> str:
    spec = config["screener"]["variants"].get(variant, {})
    if variant == "squeeze":
        return (
            "Tighten the squeeze universe: raise short float to `sh_short_o20`, "
            "require `sh_relvol_o3`, and consider `sh_price_o2` to leave the "
            "most dilution-prone band. Current filters: "
            f"{','.join(spec.get('filters', []))}"
        )
    if variant == "momentum_breakout":
        return (
            "Cut late entries: add `ta_sma20_pa10` (no more than ~10% above the SMA20 "
            "is not expressible directly — use the Technician's extension cap instead) "
            "or require `ta_highlow20d_b0to5h` so the breakout comes out of a tight range. "
            f"Current filters: {','.join(spec.get('filters', []))}"
        )
    if variant == "etf_momentum":
        return (
            "Raise the liquidity floor to `sh_avgvol_o1000` and exclude leveraged "
            "products by name in the Skeptic, since FinViz has no leverage filter. "
            f"Current filters: {','.join(spec.get('filters', []))}"
        )
    return f"Review the filter set: {','.join(spec.get('filters', []))}"


def render_markdown(analysis: dict[str, Any]) -> str:
    stats = analysis["stats"]
    lines = [
        "# Lowcap Call Tracker — Proposed Improvements",
        "",
        f"**Generated:** {analysis['generated_at']}  ",
        f"**Window:** last {analysis['lookback_days']} days — "
        f"{analysis['calls_in_window']} calls, {analysis['resolved_in_window']} priced  ",
        f"**Minimum samples before a conclusion:** {analysis['min_samples']}",
        "",
        "> Nothing here is applied automatically. Each item names the file or config "
        "key to change; approve the ones you want and edit them yourself (or ask "
        "Claude to apply a specific numbered item).",
        "",
        "## Evidence",
        "",
        "| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n |",
        "|---|---|---|---|---|---|",
    ]
    for role in ROLES:
        block = stats["role_accuracy"][role]
        lines.append(
            f"| {role} | {_fmt(block['avg_score_winners'])} | {_fmt(block['avg_score_others'])} "
            f"| {_fmt(block['edge'])} | {_fmt(block['corr_score_vs_pnl'])} | {block['samples']} |"
        )
    lines += [
        "",
        "| Variant | Calls | Hit rate % | Avg PnL % |",
        "|---|---|---|---|",
    ]
    for variant, block in stats["by_variant"].items():
        lines.append(
            f"| {variant} | {block['total']} | {_fmt(block['hit_rate_pct'])} "
            f"| {_fmt(block['avg_pnl_pct'])} |"
        )
    lines += [
        "",
        f"**Judge edge (TAKE − shadow avg PnL):** "
        f"{_fmt(stats['take_vs_skip']['judge_edge_avg_pnl_pct'])} "
        f"({stats['take_vs_skip']['verdict']})",
        "",
        "## Proposals",
        "",
    ]
    if not analysis["proposals"]:
        lines.append("No changes proposed: every lever is performing within expectations.")
    for index, proposal in enumerate(analysis["proposals"], start=1):
        lines += [
            f"### {index}. [{proposal['severity'].upper()}] {proposal['lever']} — `{proposal['target']}`",
            "",
            f"- **Finding:** {proposal['finding']}",
            f"- **Proposed change:** {proposal['proposal']}",
            "- **Approve?** ☐ yes  ☐ no",
            "",
        ]
    return "\n".join(lines) + "\n"


def is_due(config: dict[str, Any], *, days: int = 7) -> bool:
    path = resolve_path(config, "improvements_file")
    if not path.is_file():
        return True
    age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    return age >= days * 86400


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Weekly learning loop (proposals only)")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--write", action="store_true", help="Write improvements.md")
    parser.add_argument("--if-due", action="store_true", help="Exit 0 without work if run <7d ago")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.if_due and not is_due(config):
        print("learning loop not due yet (improvements.md is less than 7 days old)")
        return 0

    with CallDatabase(args.db or resolve_path(config, "db_path")) as db:
        analysis = analyse(db, config)

    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
    else:
        print(render_markdown(analysis))

    if args.write or args.if_due:
        path = resolve_path(config, "improvements_file")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(analysis), encoding="utf-8")
        print(f"improvements.md: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
