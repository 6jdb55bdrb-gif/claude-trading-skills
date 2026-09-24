#!/usr/bin/env python3
"""One tracker cycle: screen → role review → save calls → update prices → stats.

Designed to be the systemd timer entrypoint (every 4 hours). Ordering matters:

1. Session check. On a weekend or holiday, screening is skipped; the price
   update still runs so open calls never go stale.
2. Price update for the calls that already existed, applying the single
   auto-close rule (PnL <= ``tracker.close_threshold_pct`` → WRONG).
3. Screening + role review, inserting new calls (TAKE) and shadow calls (SKIP).
4. Statistics printed and written to ``stats.md``.
5. A Telegram summary, when a bot token is configured (see ``telegram_bot.py``).

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

from call_db import DECISION_UNREVIEWED, KIND_ACTIVE, KIND_UNREVIEWED, CallDatabase
from fetch_screener import FetchError, screen_all
from llm_client import LLMClient, current_month
from market_hours import session_state
from price_update import format_updates, update_open_calls
from role_review import (
    ReviewUnavailable,
    format_review,
    load_role_prompts,
    review_hit,
    review_hits,
    short_allowed,
)
from state_snapshot import (
    export_members,
    export_snapshot,
    import_members,
    import_snapshot,
    members_path,
    snapshot_path,
)
from stats import compute_stats, render_text, write_stats_file
from telegram_bot import notify_run

from config import load_config, load_dotenv, resolve_path


def make_run_id(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("run_%Y%m%dT%H%M%SZ")


def _check_backend(llm: Any, config: dict[str, Any], backend: str) -> dict[str, Any]:
    """Prove the role backend before the run depends on it."""
    if backend == "heuristic":
        return {"ok": True, "reason": "heuristic backend requested", "checked": False}
    if llm is None:
        return {"ok": False, "reason": "no LLM client", "checked": False}
    if not config["roles"].get("health_check", True):
        availability = llm.availability()
        return {
            "ok": bool(availability["available"]),
            "reason": availability["reason"],
            "checked": False,
        }
    result = llm.health_check()
    result["checked"] = True
    return result


def unreviewed_review(hit: dict[str, Any], reason: str) -> dict[str, Any]:
    """A call the screener found while the roles could not be run.

    It carries no scores and no direction: an UNREVIEWED call is a record that
    the screener fired, nothing more. The next healthy run reviews it.
    """
    return {
        "ticker": hit["ticker"],
        "asset_type": hit.get("asset_type", "stock"),
        "variant": hit.get("variant"),
        "price": hit.get("price"),
        "hit": hit,
        "verdicts": {},
        "decision": DECISION_UNREVIEWED,
        "confidence": None,
        "direction": None,
        "entry": hit.get("price"),
        "stop": None,
        "instrument": None,
        "strike": None,
        "expiry_date": None,
        "backend": "none",
        "notes": [f"backend down at call time: {reason}"],
    }


def review_backlog(
    db: CallDatabase,
    config: dict[str, Any],
    *,
    run_id: str,
    backend: str,
    llm: Any,
    agents_dir: str | None,
    offline: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Review the calls left UNREVIEWED by an earlier run with a dead backend.

    Their entry price and call date stand: the position was recorded when the
    screener fired, and only the opinion arrives late.
    """
    pending = db.unreviewed_calls()
    result: dict[str, Any] = {"pending": len(pending), "reviewed": [], "failed": []}
    if not pending:
        return result

    prompts = load_role_prompts(agents_dir, backend=backend)
    for row in pending:
        try:
            hit = json.loads(row["hit_json"]) if row["hit_json"] else None
        except (TypeError, json.JSONDecodeError):
            hit = None
        if not hit:
            result["failed"].append(
                {"ticker": row["ticker"], "reason": "the screener row was not kept"}
            )
            continue
        try:
            review = review_hit(
                hit, config, backend=backend, llm=llm, prompts=prompts, offline=offline
            )
        except ReviewUnavailable as exc:
            result["failed"].append({"ticker": row["ticker"], "reason": str(exc)})
            continue
        if not dry_run:
            db.apply_review(row["id"], review, run_id=run_id)
        result["reviewed"].append(
            {
                "ticker": row["ticker"],
                "call_id": row["id"],
                "decision": review["decision"],
                "confidence": review["confidence"],
                "entry_price": row["entry_price"],
                "called_on": row["call_date"],
            }
        )
    return result


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
    telegram: bool = True,
    snapshot: str | None = None,
    notify_when: str | None = None,
) -> dict[str, Any]:
    """Execute one cycle and return a structured report."""
    run_id = make_run_id(now)
    if notify_when:
        # An on-demand report should arrive even when the run changed nothing.
        config = {**config, "telegram": {**config.get("telegram", {}), "notify_when": notify_when}}
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

    resolved_db_path = db_path or resolve_path(config, "db_path")
    with CallDatabase(resolved_db_path) as db:
        # A scheduled run on a throwaway working copy starts with an empty
        # database; the snapshot carries dedupe state and PnL history across.
        snapshot_file = snapshot_path(config, snapshot)
        if snapshot_file and snapshot_file.is_file():
            report["snapshot_import"] = import_snapshot(db, snapshot_file)
        # The member list lives beside the snapshot but never inside it: it holds
        # invite codes and chat ids, and the snapshot is committed.
        members_file = members_path(config) if snapshot_file else None
        if members_file and members_file.is_file():
            import_members(db, members_file)

        if not dry_run:
            db.start_run(run_id, session_reason=session["reason"], screening_ran=screening_allowed)

        llm = LLMClient(config, spend_store=db) if backend in {"auto", "llm"} else None
        report["llm"] = (
            llm.availability() if llm else {"available": False, "reason": "heuristic backend"}
        )

        # One tiny call proves the backend before the run commits to it: a key
        # that expired, a spent balance or a blocked network is found here, once,
        # instead of five times per hit halfway through a review.
        health = _check_backend(llm, config, backend)
        report["backend_health"] = health
        if not health["ok"]:
            message = f"ERROR: role backend DOWN — {health['reason']}"
            print(message, file=sys.stderr)
            report["errors"].append(message)

        # 1. Price the calls that already exist (always, weekends included).
        report["price_update"] = update_open_calls(db, config, prices=prices)

        # 2. Catch up on anything a dead backend left unjudged. This runs before
        #    screening so a recovered backend settles the backlog first.
        if health["ok"]:
            report["backlog"] = review_backlog(
                db,
                config,
                run_id=run_id,
                backend=backend,
                llm=llm,
                agents_dir=agents_dir,
                offline=offline,
                dry_run=dry_run,
            )

        # 3. Screen + review.
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
            if health["ok"]:
                reviews = review_hits(
                    selected,
                    config,
                    backend=backend,
                    llm=llm,
                    agents_path=agents_dir,
                    offline=offline,
                )
            else:
                # Track what the screener found, claim nothing about it.
                reviews = [unreviewed_review(hit, health["reason"]) for hit in selected]
                report["unreviewed"] = len(reviews)
            report["reviews"] = reviews
            report["screening_ran"] = True
            for review in reviews:
                if dry_run:
                    report["new_calls"].append({**_call_line(review), "call_id": None})
                    continue
                call_id = db.insert_call(review, run_id=run_id, allow_short=short_allowed(config))
                if call_id is None:
                    report["duplicates_skipped"].append(review["ticker"])
                    continue
                report["new_calls"].append({**_call_line(review), "call_id": call_id})
        else:
            report["hits"] = 0

        # 4. Cost accounting, statistics.
        cost = (
            llm.persist_run_cost(run_id)
            if (llm and not dry_run)
            else (llm.run_cost.summary() if llm else {"cost_usd": 0.0})
        )
        report["llm_cost"] = cost
        report["llm_month_to_date_usd"] = llm.month_to_date_spend(current_month()) if llm else 0.0
        report["llm_cap_usd"] = llm.cap_usd() if llm else 0.0

        stats = compute_stats(db, config, backend_health=health)
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
            if snapshot_file:
                export_snapshot(db, snapshot_file)
                report["snapshot_file"] = str(snapshot_file)
            if members_file:
                export_members(db, members_file)

    # A broken or unconfigured bot must never fail a run: notify_run swallows
    # its own errors and reports what happened in the run report.
    if telegram and not dry_run:
        report["telegram"] = notify_run(report, config, db_path=resolved_db_path)
    elif telegram and dry_run:
        report["telegram"] = {"sent": False, "reason": "dry run"}

    return report


def _backend_line(report: dict[str, Any]) -> str:
    """Say plainly which backend spoke, and what it cost when it did not."""
    health = report.get("backend_health") or {}
    if health.get("ok"):
        latency = health.get("latency_ms")
        suffix = f", {latency}ms" if latency else ""
        return f"Role backend: LLM UP ({health.get('model')}{suffix})"
    if not health.get("checked") and report.get("llm", {}).get("reason") == "heuristic backend":
        return "Role backend: heuristic (requested)"
    return (
        f"Role backend: DOWN — {health.get('reason', 'unknown')}  "
        "→ hits recorded UNREVIEWED, judged on the next healthy run"
    )


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
        "reason": (review["verdicts"].get("judge") or {}).get("reason")
        or (review.get("notes") or [None])[0],
        "kind": KIND_UNREVIEWED
        if review["decision"] == DECISION_UNREVIEWED
        else (KIND_ACTIVE if review["decision"] == "TAKE" else "shadow"),
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
        _backend_line(report),
        "",
        "NEW CALLS",
    ]
    if report["new_calls"]:
        for call in report["new_calls"]:
            confidence = call["confidence"]
            lines.append(
                f"  {call['decision']:<10} {call['ticker']:<6} {call['asset_type']:<5} "
                f"{call['direction'] or '-':<5} "
                f"conf={'—' if confidence is None else confidence:<3} "
                f"entry={call['entry']} stop={call['stop'] or '—'} [{call['variant']}]"
            )
            if call["reason"]:
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
    if report.get("snapshot_import", {}).get("imported"):
        counts = report["snapshot_import"]["counts"]
        lines.append(f"  state restored from snapshot: {counts['calls']} call(s)")
    if report.get("snapshot_file"):
        lines.append(f"  snapshot: {report['snapshot_file']}")
    telegram_result = report.get("telegram")
    if telegram_result:
        status = (
            "sent" if telegram_result.get("sent") else f"not sent ({telegram_result.get('reason')})"
        )
        lines.append(f"  telegram: {status}")
    for error in report["errors"]:
        lines.append(f"  ERROR: {error}")
    if verbose:
        lines += ["", "ROLE VERDICTS"]
        for review in report["reviews"]:
            lines.append(format_review(review))
            lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # credentials may live in .env; a real env var still wins
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
    parser.add_argument("--no-telegram", action="store_true", help="Skip the Telegram notification")
    parser.add_argument(
        "--notify",
        choices=["always", "changes"],
        help="Override telegram.notify_when for this run ('always' for an on-demand report)",
    )
    parser.add_argument(
        "--snapshot",
        help="JSON state snapshot: imported into an empty database, rewritten after the run",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Test the role backend with one tiny API call and exit",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Also print every role verdict")
    args = parser.parse_args(argv)

    config = load_config(args.config)

    if args.health_check:
        with CallDatabase(args.db or resolve_path(config, "db_path")) as db:
            health = _check_backend(LLMClient(config, spend_store=db), config, args.backend)
        if args.json:
            print(json.dumps(health, indent=2, default=str))
        elif health["ok"]:
            print(
                f"BACKEND UP — {health.get('model')} answered in "
                f"{health.get('latency_ms', '?')}ms, "
                f"${health.get('cost_usd', 0):.6f}, "
                f"${health.get('cap_remaining_usd', 0):.2f} left this month"
            )
        else:
            print(f"BACKEND DOWN — {health['reason']}", file=sys.stderr)
        return 0 if health["ok"] else 1
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
        telegram=not args.no_telegram,
        snapshot=args.snapshot,
        notify_when=args.notify,
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
