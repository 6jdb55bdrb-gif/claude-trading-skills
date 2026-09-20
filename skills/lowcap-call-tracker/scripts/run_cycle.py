#!/usr/bin/env python3
"""One tracker cycle: screen → role review → save calls → update prices → stats.

Designed to be the systemd timer entrypoint (every 4 hours). Ordering matters:

1. Session check. On a weekend or holiday, screening is skipped; the price
   update still runs so open calls never go stale.
2. Price update for the calls that already existed, applying the single
   auto-close rule (PnL <= ``tracker.close_threshold_pct`` → WRONG).
3. Screening + role review, inserting new calls (TAKE) and shadow calls (SKIP).
4. Statistics printed and written to ``stats.md``.

CLI:
    python3 run_cycle.py --dry-run --fixture fixtures/dry_run_hits.json
    python3 run_cycle.py --backend heuristic --prices-json '{"SQZX": 4.1}'
    python3 run_cycle.py --git-push
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from call_db import KIND_ACTIVE, CallDatabase
from fetch_screener import FetchError, screen_all
from llm_client import LLMClient, current_month
from market_hours import session_state
from price_update import format_updates, update_open_calls
from role_review import format_review, review_hits
from stats import compute_stats, render_text, write_stats_file

from config import load_config, resolve_path


def make_run_id(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("run_%Y%m%dT%H%M%SZ")


def _select_hits(
    db: CallDatabase, hits: list[dict[str, Any]], limit: int
) -> tuple[list, list[str]]:
    """Drop hits that already hold an open call; cap the rest at *limit*."""
    selected: list[dict[str, Any]] = []
    duplicates: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        ticker = str(hit.get("ticker", "")).upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        if db.open_call_for(ticker):
            duplicates.append(ticker)
            continue
        selected.append(hit)
    return selected[: max(0, limit)], duplicates


def run_cycle(
    config: dict[str, Any],
    *,
    backend: str = "auto",
    fixture: str | None = None,
    screen_mode: str | None = None,
    prices: dict[str, float] | None = None,
    variants: list[str] | None = None,
    agents_dir: str | None = None,
    force_screen: bool = False,
    dry_run: bool = False,
    offline: bool = False,
    now: datetime | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Execute one cycle and return a structured report."""
    run_id = make_run_id(now)
    session = session_state(config, now)
    screening_allowed = session["screening_allowed"] or force_screen
    report: dict[str, Any] = {
        "run_id": run_id,
        "session": session,
        "screening_ran": False,
        "dry_run": dry_run,
        "new_calls": [],
        "duplicates_skipped": [],
        "reviews": [],
        "price_update": {"priced": 0, "closed": 0, "updates": [], "missing_prices": []},
        "errors": [],
    }

    with CallDatabase(db_path or resolve_path(config, "db_path")) as db:
        if not dry_run:
            db.start_run(run_id, session_reason=session["reason"], screening_ran=screening_allowed)

        llm = LLMClient(config, spend_store=db) if backend in {"auto", "llm"} else None
        report["llm"] = (
            llm.availability() if llm else {"available": False, "reason": "heuristic backend"}
        )

        # 1. Price the calls that already exist (always, weekends included).
        report["price_update"] = update_open_calls(db, config, prices=prices)

        # 2. Screen + review.
        if screening_allowed:
            try:
                hits = screen_all(config, mode=screen_mode, fixture=fixture, variants=variants)
            except FetchError as exc:
                hits = []
                report["errors"].append(f"screening failed: {exc}")
            report["hits"] = len(hits)
            selected, duplicates = _select_hits(
                db, hits, int(config["tracker"].get("max_new_calls_per_run", 10))
            )
            report["duplicates_skipped"] = duplicates
            reviews = review_hits(
                selected,
                config,
                backend=backend,
                llm=llm,
                agents_path=agents_dir,
                offline=offline,
            )
            report["reviews"] = reviews
            report["screening_ran"] = True
            for review in reviews:
                if dry_run:
                    report["new_calls"].append({**_call_line(review), "call_id": None})
                    continue
                call_id = db.insert_call(review, run_id=run_id)
                if call_id is None:
                    report["duplicates_skipped"].append(review["ticker"])
                    continue
                report["new_calls"].append({**_call_line(review), "call_id": call_id})
        else:
            report["hits"] = 0

        # 3. Cost accounting, statistics.
        cost = (
            llm.persist_run_cost(run_id)
            if (llm and not dry_run)
            else (llm.run_cost.summary() if llm else {"cost_usd": 0.0})
        )
        report["llm_cost"] = cost
        report["llm_month_to_date_usd"] = llm.month_to_date_spend(current_month()) if llm else 0.0
        report["llm_cap_usd"] = llm.cap_usd() if llm else 0.0

        stats = compute_stats(db, config)
        report["stats"] = stats
        if not dry_run:
            takes = sum(1 for call in report["new_calls"] if call["decision"] == "TAKE")
            db.finish_run(
                run_id,
                {
                    "hits": report.get("hits", 0),
                    "reviewed": len(report["reviews"]),
                    "new_calls": len(report["new_calls"]),
                    "new_takes": takes,
                    "new_shadows": len(report["new_calls"]) - takes,
                    "closed": report["price_update"]["closed"],
                    "priced": report["price_update"]["priced"],
                    "backend": backend,
                    "llm_cost_usd": cost.get("cost_usd", 0.0),
                    "notes": "; ".join(report["errors"])[:500] or None,
                },
            )
            report["stats_file"] = write_stats_file(stats, config)

    return report


def _call_line(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticker": review["ticker"],
        "asset_type": review["asset_type"],
        "variant": review["variant"],
        "direction": review.get("direction"),
        "decision": review["decision"],
        "confidence": review["confidence"],
        "entry": review.get("entry"),
        "stop": review.get("stop"),
        "reason": (review["verdicts"].get("judge") or {}).get("reason"),
        "kind": KIND_ACTIVE if review["decision"] == "TAKE" else "shadow",
    }


def format_report(report: dict[str, Any], *, verbose: bool = False) -> str:
    session = report["session"]
    lines = [
        "=" * 72,
        f"LOWCAP CALL TRACKER — {report['run_id']}"
        + ("  [DRY RUN]" if report.get("dry_run") else ""),
        "=" * 72,
        f"Session: {session['as_of']} — {session['reason']}"
        + ("" if report["screening_ran"] else "  → screening skipped, price update only"),
        f"Role backend: {'LLM' if report['llm'].get('available') else 'heuristic'} "
        f"({report['llm'].get('reason')})",
        "",
        "NEW CALLS",
    ]
    if report["new_calls"]:
        for call in report["new_calls"]:
            lines.append(
                f"  {call['decision']:<4} {call['ticker']:<6} {call['asset_type']:<5} "
                f"{call['direction'] or '-':<5} conf={call['confidence']:<3} "
                f"entry={call['entry']} stop={call['stop']} [{call['variant']}]"
            )
            lines.append(f"       {call['reason']}")
    else:
        lines.append("  (none)")
    if report["duplicates_skipped"]:
        lines.append(f"  already open, not duplicated: {', '.join(report['duplicates_skipped'])}")

    lines += ["", "OPEN CALLS — PRICE UPDATE", format_updates(report["price_update"])]
    closed = [update for update in report["price_update"]["updates"] if update["closed"]]
    lines += ["", "CLOSED THIS RUN"]
    if closed:
        for update in closed:
            lines.append(
                f"  {update['ticker']:<6} pnl={update['pnl_pct']:+.1f}% "
                f"<= {report['price_update']['threshold_pct']}% → WRONG"
            )
    else:
        lines.append("  (none)")

    lines += ["", render_text(report["stats"])]
    cost = report.get("llm_cost", {})
    lines.append(
        f"  LLM cost this run: ${cost.get('cost_usd', 0.0):.4f} "
        f"({cost.get('calls', 0)} calls, {cost.get('input_tokens', 0)} in / "
        f"{cost.get('output_tokens', 0)} out) | month-to-date "
        f"${report.get('llm_month_to_date_usd', 0.0):.4f} of ${report.get('llm_cap_usd', 0.0):.2f} cap"
    )
    if report.get("stats_file"):
        lines.append(f"  stats.md: {report['stats_file']}")
    for error in report["errors"]:
        lines.append(f"  ERROR: {error}")
    if verbose:
        lines += ["", "ROLE VERDICTS"]
        for review in report["reviews"]:
            lines.append(format_review(review))
            lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one lowcap tracker cycle")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--backend", choices=["auto", "llm", "heuristic"], default="auto")
    parser.add_argument("--fixture", help="Screen from a JSON fixture instead of the network")
    parser.add_argument("--screen-mode", choices=["auto", "elite", "public", "fixture"])
    parser.add_argument("--variant", action="append", dest="variants")
    parser.add_argument("--prices-json", help="Offline ticker -> price mapping for the update")
    parser.add_argument("--agents-dir", help="Directory holding lowcap-*.md role prompts")
    parser.add_argument("--force-screen", action="store_true", help="Screen even when closed")
    parser.add_argument("--dry-run", action="store_true", help="Review without writing calls")
    parser.add_argument("--offline", action="store_true", help="Skip network-dependent adapters")
    parser.add_argument("--git-push", action="store_true", help="Push stats.md / improvements.md")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Also print every role verdict")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    report = run_cycle(
        config,
        backend=args.backend,
        fixture=args.fixture,
        screen_mode=args.screen_mode,
        prices=json.loads(args.prices_json) if args.prices_json else None,
        variants=args.variants,
        agents_dir=args.agents_dir,
        force_screen=args.force_screen,
        dry_run=args.dry_run,
        offline=args.offline or args.backend == "heuristic",
        db_path=args.db,
    )

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_report(report, verbose=args.verbose))

    if args.git_push and not args.dry_run:
        from publish import publish_reports

        result = publish_reports(config, message=f"chore(lowcap-tracker): {report['run_id']} stats")
        print(f"  git push: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
