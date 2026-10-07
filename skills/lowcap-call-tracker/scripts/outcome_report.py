#!/usr/bin/env python3
"""The screener scorecard: v1 against v2, on outcomes rather than on opinion.

Two generations of filters only earn their keep if the calls they produced can
be compared. This report does that comparison per variant and per confidence
bucket, and it reports the Judge's own edge — the gap between what it took and
what it refused — because a Judge that skips the winners is worse than no Judge.

It recommends and never applies. ``min_confidence_to_take`` and
``no_catalyst_penalty`` are the two dials that decide what gets traded, and a
loop that moves them on its own would be optimising itself against a few weeks
of noise. The numbers and the proposal go in the report; the edit is the
operator's.

CLI:
    python3 outcome_report.py
    python3 outcome_report.py --json
    python3 outcome_report.py --fill        # measure first, then report
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from call_db import CallDatabase
from outcome_tracker import fill_outcomes, settled_return

from config import load_config, load_dotenv, resolve_path

# The buckets the operator asked for, plus a floor bucket: a call can be logged
# below the take threshold (every SKIP is), and leaving those out would hide
# exactly the calls that justify the threshold.
CONFIDENCE_BUCKETS = ("<50", "50-59", "60-69", "70+", "unknown")
BUCKET_FLOORS = {"50-59": 50, "60-69": 60, "70+": 70}

# Below this, a slice is reported but never used as the basis of a proposal:
# four calls is an anecdote.
MIN_SAMPLES = 5
# The operator's gate for putting the scorecard in the Telegram summary.
TELEGRAM_MIN_CALLS = 30


def bucket_for(confidence: Any) -> str:
    """Which confidence bucket a call belongs to."""
    if confidence is None:
        return "unknown"
    try:
        value = int(float(confidence))
    except (TypeError, ValueError):
        return "unknown"
    if value >= 70:
        return "70+"
    if value >= 60:
        return "60-69"
    if value >= 50:
        return "50-59"
    return "<50"


def _slice(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Hit rate, average return and stop-hit rate for one group of calls."""
    returns = [row["settled"] for row in rows]
    stopped = sum(1 for row in rows if row["stopped_out"])
    wins = sum(1 for value in returns if value > 0)
    count = len(rows)
    # The stop-hit rate is measured over the calls that actually carried a
    # stop. The book predates tracker.sl_pct, and reporting those calls as 0%
    # stopped would claim the stop was never hit rather than never set.
    with_stop = sum(1 for row in rows if row.get("sl_price") is not None)
    return {
        "calls": count,
        "calls_with_stop": with_stop,
        "hit_rate_pct": round(100.0 * wins / count, 1) if count else None,
        "avg_return_pct": round(sum(returns) / count, 2) if count else None,
        "best_return_pct": round(max(returns), 2) if count else None,
        "worst_return_pct": round(min(returns), 2) if count else None,
        "stop_hit_rate_pct": round(100.0 * stopped / with_stop, 1) if with_stop else None,
        "enough_samples": count >= MIN_SAMPLES,
    }


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        out.setdefault(row[key], []).append(row)
    return {
        name: _slice(group) for name, group in sorted(out.items(), key=lambda item: str(item[0]))
    }


def measured_calls(db: CallDatabase, config: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Every live call with at least one elapsed horizon, plus the pending count.

    VOID rows are excluded: a voided call is a duplicate reversed by hand, and a
    clerical error does not belong in the Judge's record.

    A call is "measured" on the longest horizon that has elapsed, so a
    three-day-old call still counts — on its three-day number.
    """
    floor = float((config["roles"].get("judge") or {}).get("catalyst_score_floor", 4.0))
    rows: list[dict[str, Any]] = []
    pending = 0
    cursor = db.conn.execute(
        """
        SELECT id, ticker, call_date, screener_version, screen_variant, judge_decision,
               confidence, researcher_score, entry_price, sl_price, ret_1d, ret_3d, ret_5d,
               COALESCE(stopped_out, 0) AS stopped_out
          FROM calls
         WHERE status <> 'VOID'
         ORDER BY call_date, id
        """
    )
    for raw in cursor:
        row = dict(raw)
        settled = settled_return(row)
        if settled is None:
            pending += 1
            continue
        score = row["researcher_score"]
        rows.append(
            {
                **row,
                "settled": settled,
                "stopped_out": bool(row["stopped_out"]),
                # The Judge charges for a missing catalyst off the Researcher's
                # score, so the report has to read "catalyst" the same way the
                # penalty did, not from a second opinion.
                "catalyst": score is not None and float(score) >= floor,
                # An untagged row predates the version switch; it is v1 by
                # definition, since v1 is what produced it.
                "version": str(row["screener_version"] or "v1"),
                "variant": str(row["screen_variant"] or "unknown"),
                "decision": str(row["judge_decision"] or "unknown"),
                "bucket": bucket_for(row["confidence"]),
            }
        )
    return rows, pending


def build_report(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    rows, pending = measured_calls(db, config)
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_calls": len(rows),
        "pending": pending,
        "min_samples": MIN_SAMPLES,
        "telegram_min_calls": TELEGRAM_MIN_CALLS,
        "telegram_ready": len(rows) >= TELEGRAM_MIN_CALLS,
        "versions": {},
        "buckets": _group(rows, "bucket") if rows else {},
        "catalyst": {
            "with": _slice([row for row in rows if row["catalyst"]]),
            "without": _slice([row for row in rows if not row["catalyst"]]),
        }
        if rows
        else {},
    }
    for version, group in sorted(_bucket_by(rows, "version").items()):
        block = _slice(group)
        block["variants"] = _group(group, "variant")
        block["buckets"] = _group(group, "bucket")
        block["decisions"] = _group(group, "decision")
        takes = block["decisions"].get("TAKE", {}).get("avg_return_pct")
        skips = block["decisions"].get("SKIP", {}).get("avg_return_pct")
        # Positive means the Judge's TAKEs beat what it waved away.
        block["judge_edge_pct"] = (
            round(takes - skips, 2) if takes is not None and skips is not None else None
        )
        report["versions"][version] = block
    return report


def _bucket_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        out.setdefault(row[key], []).append(row)
    return out


def recommendations(report: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """What the numbers would argue for. Nothing here is applied."""
    judge = config["roles"].get("judge") or {}
    out: list[dict[str, Any]] = []

    # --- the take threshold ------------------------------------------------
    current_threshold = int(judge.get("min_confidence_to_take", 55))
    buckets = report.get("buckets") or {}
    losing = [
        (name, stats)
        for name, stats in buckets.items()
        if name in BUCKET_FLOORS
        and stats.get("enough_samples")
        and (stats.get("avg_return_pct") or 0) < 0
    ]
    paying = [
        (name, stats)
        for name, stats in buckets.items()
        if name in BUCKET_FLOORS
        and stats.get("enough_samples")
        and (stats.get("avg_return_pct") or 0) > 0
    ]
    if losing and paying:
        worst_floor = max(BUCKET_FLOORS[name] for name, _ in losing)
        # Raised to just above the highest band that has actually lost money,
        # not to the next band that has made some: skipping an unmeasured band
        # would throw away calls on no evidence at all.
        proposed = min(worst_floor + 10, max(BUCKET_FLOORS.values()))
        pays_higher = any(BUCKET_FLOORS[name] > worst_floor for name, _ in paying)
        if pays_higher and proposed != current_threshold:
            detail = ", ".join(
                f"{name} avg {stats['avg_return_pct']:+.1f}% over {stats['calls']} calls"
                for name, stats in sorted(losing + paying, key=lambda item: item[0])
            )
            out.append(
                {
                    "setting": "roles.judge.min_confidence_to_take",
                    "current": current_threshold,
                    "proposed": proposed,
                    "applied": False,
                    "why": f"{detail}. Confidence below {proposed} has not paid.",
                }
            )

    # --- the catalyst penalty ---------------------------------------------
    current_penalty = int(judge.get("no_catalyst_penalty", 0) or 0)
    catalyst = report.get("catalyst") or {}
    with_stats = catalyst.get("with") or {}
    without_stats = catalyst.get("without") or {}
    if with_stats.get("enough_samples") and without_stats.get("enough_samples"):
        gap = (with_stats["avg_return_pct"] or 0) - (without_stats["avg_return_pct"] or 0)
        # One point of penalty per 2 points of return the gap is worth, clamped
        # to a range a human would recognise. Deliberately coarse: the point is
        # the direction of the evidence, not a fitted coefficient.
        proposed = max(0, min(40, round(abs(gap) / 2.0 / 5.0) * 5)) if gap > 0 else 0
        if gap > 0 and proposed > current_penalty:
            out.append(
                {
                    "setting": "roles.judge.no_catalyst_penalty",
                    "current": current_penalty,
                    "proposed": int(proposed),
                    "applied": False,
                    "why": (
                        f"calls with a catalyst averaged {with_stats['avg_return_pct']:+.1f}% "
                        f"against {without_stats['avg_return_pct']:+.1f}% without one "
                        f"({with_stats['calls']} vs {without_stats['calls']} calls): the "
                        "penalty is charging less than the evidence supports"
                    ),
                }
            )
        elif gap <= 0 and current_penalty > 0:
            out.append(
                {
                    "setting": "roles.judge.no_catalyst_penalty",
                    "current": current_penalty,
                    "proposed": 0,
                    "applied": False,
                    "why": (
                        f"calls without a catalyst averaged {without_stats['avg_return_pct']:+.1f}% "
                        f"against {with_stats['avg_return_pct']:+.1f}% with one: the penalty is "
                        "charging for nothing"
                    ),
                }
            )
    return out


def _row_line(label: str, stats: dict[str, Any], width: int = 18) -> str:
    return (
        f"  {label:<{width}} n={stats['calls']:<3} "
        f"hit={_pct(stats['hit_rate_pct'])} "
        f"avg={_signed(stats['avg_return_pct'])} "
        f"stopped={_pct(stats['stop_hit_rate_pct'])}"
        + ("" if stats.get("calls_with_stop") else "  (no stop set)")
        + ("" if stats["enough_samples"] else "  (thin)")
    )


def _pct(value: Any) -> str:
    return "—" if value is None else f"{value:>5.1f}%"


def _signed(value: Any) -> str:
    return "—" if value is None else f"{value:+6.2f}%"


def render_report(report: dict[str, Any], *, config: dict[str, Any] | None = None) -> str:
    lines = [
        "=" * 72,
        "SCREENER SCORECARD — v1 vs v2",
        "=" * 72,
        f"Measured calls: {report['total_calls']}  (pending: {report['pending']})",
    ]
    if not report["total_calls"]:
        lines.append("")
        lines.append("  No measured calls yet — returns appear one session after the first call.")
        return "\n".join(lines)

    for version, block in report["versions"].items():
        lines += ["", f"{version.upper()}  {_row_line('all calls', block).strip()}"]
        edge = block.get("judge_edge_pct")
        if edge is not None:
            verdict = "TAKEs beat SKIPs" if edge > 0 else "SKIPs beat TAKEs"
            lines.append(f"  judge edge: {edge:+.2f}%  ({verdict})")
        lines.append("  by variant:")
        for name, stats in block["variants"].items():
            lines.append(_row_line(name, stats))
        lines.append("  by confidence:")
        for name in CONFIDENCE_BUCKETS:
            if name in block["buckets"]:
                lines.append(_row_line(name, block["buckets"][name]))
        lines.append("  by decision:")
        for name, stats in block["decisions"].items():
            lines.append(_row_line(name, stats))

    catalyst = report.get("catalyst") or {}
    if catalyst:
        lines += ["", "CATALYST"]
        lines.append(_row_line("with catalyst", catalyst["with"]))
        lines.append(_row_line("without", catalyst["without"]))

    if config is not None:
        proposals = recommendations(report, config)
        lines += ["", "RECOMMENDATIONS — not applied, nothing here changes the config"]
        if not proposals:
            lines.append("  (none: the thresholds match what the numbers support)")
        for item in proposals:
            lines.append(f"  {item['setting']}: {item['current']} → {item['proposed']}")
            lines.append(f"      {item['why']}")
        lines.append("  Edit assets/tracker_config.yaml yourself if you agree.")

    if not report["telegram_ready"]:
        lines += [
            "",
            f"  Held out of the Telegram summary until {report['telegram_min_calls']} "
            f"measured calls ({report['total_calls']} so far).",
        ]
    return "\n".join(lines)


def telegram_summary(report: dict[str, Any], config: dict[str, Any] | None = None) -> str | None:
    """A compact scorecard for the run message, or None while the sample is thin."""
    if not report.get("telegram_ready"):
        return None
    lines = [f"📊 *Scorecard* ({report['total_calls']} calls)"]
    for version, block in report["versions"].items():
        lines.append(
            f"{version}: n={block['calls']} hit={_pct(block['hit_rate_pct']).strip()} "
            f"avg={_signed(block['avg_return_pct']).strip()} "
            f"stopped={_pct(block['stop_hit_rate_pct']).strip()}"
        )
    for item in recommendations(report, config) if config else []:
        lines.append(
            f"proposal (not applied): {item['setting']} {item['current']}→{item['proposed']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Report call outcomes by screener version")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--fill", action="store_true", help="Fill outcomes before reporting")
    parser.add_argument("--as-of", help="Treat this YYYY-MM-DD as today (replay)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    with CallDatabase(args.db or resolve_path(config, "db_path")) as db:
        filled = fill_outcomes(db, config, as_of=args.as_of) if args.fill else None
        report = build_report(db, config)

    if args.json:
        print(
            json.dumps(
                {
                    "fill": filled,
                    "report": report,
                    "recommendations": recommendations(report, config),
                },
                indent=2,
                default=str,
            )
        )
    else:
        if filled:
            print(f"filled {filled['updated']} of {filled['pending']} pending calls\n")
        print(render_report(report, config=config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
