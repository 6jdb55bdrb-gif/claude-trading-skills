#!/usr/bin/env python3
"""Move the OPEN positions onto the trailing stop the config now says.

A call stores its own trail distance, resolved from the config at entry, so
that editing a setting never re-stops a position somebody is already holding.
That default is right — a stop that moves with the config is not a stop — but
it means changing ``tracker.trailing_stop_pct`` changes new calls only. When
the operator changes the rule and means it for the whole book, this is the one
deliberate step that moves the open positions onto it.

Two things make it safe to run:

* ``plan_retrail`` writes nothing. It reports, per open call, the distance it
  moves from, the distance it moves to, the resulting stop price, and how far
  below its own high-water mark it is sitting right now.
* A call already further below its peak than the new distance is named as
  ``would_stop``. Tightening a trail onto such a position is an exit, not a
  setting, and it has to be seen before it is taken. ``only_widen`` leaves
  exactly those calls on the distance they were taken with.

Applying the change writes the distance and nothing else. The close, if one is
due, belongs to the next price update — the only code that compares a trail to
a price somebody actually paid, stamps the exit and books the PnL.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from call_db import STATUS_OPEN, CallDatabase, resolve_trail_pct

from config import load_config, resolve_path


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def target_trail(config: dict[str, Any], row: Any) -> float | None:
    """The distance *row* would be given if it were opened today."""
    tracker = config["tracker"]
    hit = {}
    try:
        import json

        hit = json.loads(row["hit_json"] or "{}") or {}
    except (ValueError, TypeError, IndexError, KeyError):
        hit = {}
    return resolve_trail_pct(
        row["entry_price"],
        hit.get("atr"),
        floor_pct=tracker.get("trailing_stop_pct"),
        atr_mult=tracker.get("trailing_stop_atr_mult"),
    )


def plan_retrail(db: CallDatabase, config: dict[str, Any]) -> list[dict[str, Any]]:
    """What re-setting the trail would do to each open call. Writes nothing.

    Raises when the config has no trailing stop at all: "re-set every open
    position to no stop" is a plausible reading of that and a terrible one.
    """
    if _number(config["tracker"].get("trailing_stop_pct")) is None:
        raise ValueError(
            "config has no trailing stop (tracker.trailing_stop_pct is null) — "
            "refusing to re-set open calls to no stop at all"
        )

    plan: list[dict[str, Any]] = []
    for row in db.open_calls():
        new_pct = target_trail(config, row)
        if new_pct is None:
            continue
        old_pct = _number(row["trail_pct"])
        peak = _number(row["peak_price"]) or _number(row["entry_price"])
        price = _number(row["current_price"]) or _number(row["entry_price"])
        drop = round((price - peak) / peak * 100.0, 2) if peak else 0.0
        plan.append(
            {
                "call_id": row["id"],
                "ticker": row["ticker"],
                "from_pct": old_pct,
                "to_pct": new_pct,
                "direction": "unchanged"
                if old_pct is not None and abs(old_pct - new_pct) < 0.05
                else ("tighter" if old_pct is not None and new_pct < old_pct else "wider"),
                "peak": peak,
                "price": price,
                "drop_pct": drop,
                "old_stop": round(peak * (1 - old_pct / 100.0), 2)
                if peak and old_pct is not None
                else None,
                "new_stop": round(peak * (1 - new_pct / 100.0), 2) if peak else None,
                # Already past the new line. The next price update closes it.
                "would_stop": bool(peak and drop <= -new_pct),
            }
        )
    return plan


def apply_retrail(
    db: CallDatabase,
    config: dict[str, Any],
    *,
    only_widen: bool = False,
) -> dict[str, Any]:
    """Write the new distance onto the open calls. Closes nothing."""
    plan = plan_retrail(db, config)
    changed: list[str] = []
    skipped: list[str] = []
    for entry in plan:
        if entry["direction"] == "unchanged":
            continue
        if only_widen and entry["direction"] == "tighter":
            skipped.append(entry["ticker"])
            continue
        db.conn.execute(
            "UPDATE calls SET trail_pct = ? WHERE id = ? AND status = ?",
            (entry["to_pct"], entry["call_id"], STATUS_OPEN),
        )
        changed.append(entry["ticker"])
    db.conn.commit()
    return {
        "plan": plan,
        "changed": len(changed),
        "tickers": changed,
        "skipped": skipped,
        "would_stop": [
            entry["ticker"] for entry in plan if entry["would_stop"] and entry["ticker"] in changed
        ],
    }


def format_plan(plan: list[dict[str, Any]]) -> str:
    lines = [
        f"{'ticker':<8}{'from':>7}{'to':>7}{'peak':>9}{'now':>9}{'off peak':>10}"
        f"{'old stop':>10}{'new stop':>10}  note",
    ]
    for entry in plan:
        note = "would close on the next price update" if entry["would_stop"] else entry["direction"]
        old = "—" if entry["from_pct"] is None else f"{entry['from_pct']:.1f}%"
        old_stop = "—" if entry["old_stop"] is None else f"{entry['old_stop']:.2f}"
        lines.append(
            f"{entry['ticker']:<8}{old:>7}{entry['to_pct']:>6.1f}%"
            f"{entry['peak'] or 0:>9.2f}{entry['price'] or 0:>9.2f}"
            f"{entry['drop_pct']:>9.1f}%{old_stop:>10}{entry['new_stop'] or 0:>10.2f}  {note}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--db", default=None)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the new distances (without this, the plan is printed and nothing changes)",
    )
    parser.add_argument(
        "--only-widen",
        action="store_true",
        help="skip any call the new distance would tighten, so no position is exited",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    db_path = args.db or resolve_path(config, "db_path")
    with CallDatabase(db_path) as db:
        if args.apply:
            result = apply_retrail(db, config, only_widen=args.only_widen)
            print(format_plan(result["plan"]))
            print(f"\nchanged {result['changed']} open call(s)")
            if result["skipped"]:
                print(f"left alone (--only-widen): {', '.join(result['skipped'])}")
            if result["would_stop"]:
                print(
                    "the next price update will close: " + ", ".join(result["would_stop"]),
                    file=sys.stderr,
                )
        else:
            plan = plan_retrail(db, config)
            print(format_plan(plan) if plan else "no open calls")
            print("\n(plan only — nothing written; pass --apply to write it)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
