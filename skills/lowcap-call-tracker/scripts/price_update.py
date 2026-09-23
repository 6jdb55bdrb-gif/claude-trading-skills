#!/usr/bin/env python3
"""Refresh prices for every open call and apply the single auto-close rule.

Prices come from yfinance (free, no key). The update runs on every tracker run —
including weekends and holidays, when screening is skipped — so a call's PnL is
never stale by more than one cycle.

CLI:
    python3 price_update.py --db state/lowcap_calls.db
    python3 price_update.py --prices-json '{"SQZX": 1.10}'   # offline replay
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

from call_db import CallDatabase, pnl_pct
from option_contract import days_to_expiry, is_expired

from config import load_config, resolve_path

try:
    import yfinance

    HAS_YFINANCE = True
except ImportError:  # pragma: no cover - offline installs pass --prices-json
    HAS_YFINANCE = False


def _age_days(stamp: Any, now: datetime) -> int | None:
    """Whole days between an ISO timestamp and *now*; None when it cannot be parsed."""
    if not stamp:
        return None
    try:
        moment = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0, (now - moment).days)


def _download_closes(tickers: list[str]) -> dict[str, list[tuple[str, float]]]:
    """Daily closes per ticker as ``[(YYYY-MM-DD, close), ...]``, oldest first.

    NaN closes are kept: a forming session publishes a bar with volume and no
    close yet, and the caller has to know that bar exists.
    """
    if not tickers or not HAS_YFINANCE:
        return {}
    series: dict[str, list[tuple[str, float]]] = {}
    unique = sorted(set(tickers))
    try:
        data = yfinance.download(
            tickers=" ".join(unique),
            period="5d",
            interval="1d",
            progress=False,
            group_by="ticker",
            auto_adjust=False,
            threads=False,
        )
    except Exception:  # pragma: no cover - network/provider failure
        data = None

    if data is not None and not getattr(data, "empty", True):
        for ticker in unique:
            try:
                column = data[ticker]["Close"] if len(unique) > 1 else data["Close"]
                series[ticker] = [
                    (str(index.date()), float(value)) for index, value in column.items()
                ]
            except (KeyError, IndexError, TypeError, AttributeError):
                continue

    for ticker in [name for name in unique if name not in series]:  # pragma: no cover
        try:
            column = yfinance.Ticker(ticker).history(period="5d")["Close"]
            series[ticker] = [(str(index.date()), float(value)) for index, value in column.items()]
        except Exception:
            continue
    return series


def fetch_price_points(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """Return ``{ticker: {"price": float, "as_of": "YYYY-MM-DD"}}``.

    The session the close belongs to travels with the price. Without it an
    overnight run cannot tell a fresh close from the previous one, and silently
    marks every position back to a stale session — which is exactly what it did
    before this returned a date.
    """
    points: dict[str, dict[str, Any]] = {}
    for ticker, rows in _download_closes(tickers).items():
        for as_of, close in reversed(rows):
            if close is None or close != close:  # NaN: the bar has not closed
                continue
            points[ticker] = {"price": float(close), "as_of": as_of}
            break
    return points


def fetch_prices(tickers: list[str]) -> dict[str, float]:
    """Return {ticker: last price}; missing tickers are simply absent."""
    return {ticker: point["price"] for ticker, point in fetch_price_points(tickers).items()}


def _as_points(prices: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Accept either ``{ticker: price}`` or ``{ticker: {price, as_of}}``.

    A bare number carries no session, so it is always applied — that is what a
    caller passing ``--prices-json`` or a fixture means.
    """
    points: dict[str, dict[str, Any]] = {}
    for ticker, value in (prices or {}).items():
        if isinstance(value, dict):
            points[ticker] = {"price": float(value["price"]), "as_of": value.get("as_of")}
        else:
            points[ticker] = {"price": float(value), "as_of": None}
    return points


def update_open_calls(
    db: CallDatabase,
    config: dict[str, Any],
    *,
    prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Price every open call, apply the close rule, and summarize the result."""
    raw_threshold = config["tracker"].get("close_threshold_pct")
    threshold = None if raw_threshold is None else float(raw_threshold)
    close_on_expiry = bool(config["tracker"].get("close_on_expiry", True))
    open_calls = db.open_calls()
    tickers = [row["ticker"] for row in open_calls]
    # An explicitly empty mapping means "offline, no prices" — not "go fetch".
    resolved = _as_points(prices) if prices is not None else fetch_price_points(tickers)
    stale_sources: list[str] = []

    updates: list[dict[str, Any]] = []
    missing: list[str] = []
    now = datetime.now(timezone.utc)
    for row in open_calls:
        point = resolved.get(row["ticker"])
        price = point["price"] if point else None
        as_of = (point or {}).get("as_of")
        # A price from an earlier session than the one already recorded is a
        # regression, not an update: the provider is offering yesterday's close
        # because today's bar has not settled. Keep the newer mark.
        regressed = bool(as_of and row["price_as_of"] and as_of < row["price_as_of"])
        if regressed:
            stale_sources.append(row["ticker"])
            price = None
        common = {
            "direction": row["direction"],
            "instrument": row["instrument"],
            "expiry_date": row["expiry_date"],
            "strike": row["strike"],
            "days_to_expiry": days_to_expiry(row["expiry_date"]),
            "kind": row["kind"],
            "entry_price": row["entry_price"],
            "variant": row["screen_variant"],
            "asset_type": row["asset_type"],
            "call_date": row["call_date"],
            "age_days": _age_days(row["call_date"], now),
        }
        if price is None:
            # An open call that cannot be priced must still be REPORTED, with its
            # last known figures and how stale they are — dropping it from the
            # report is how a position quietly disappears.
            if not regressed:
                missing.append(row["ticker"])
            updates.append(
                {
                    "call_id": row["id"],
                    "ticker": row["ticker"],
                    "price": row["current_price"],
                    "pnl_pct": row["pnl_pct"],
                    "closed": False,
                    "priced": False,
                    "stale_source": regressed,
                    "last_price_at": row["last_price_at"],
                    "stale_days": _age_days(row["last_price_at"], now),
                    **common,
                }
            )
            continue
        result = db.apply_price(row["id"], float(price), close_threshold_pct=threshold, as_of=as_of)
        result["stale_source"] = False
        result.update({"priced": True, "stale_days": 0, **common})
        updates.append(result)

    # Settle expired contracts last, so each one books its freshest price.
    if close_on_expiry:
        for update in updates:
            if update.get("closed") or not is_expired(update.get("expiry_date")):
                continue
            settled = db.expire_call(update["call_id"])
            update.update({"closed": True, "expired": True, "pnl_pct": settled["pnl_pct"]})

    return {
        "priced": sum(1 for update in updates if update["priced"]),
        "open": len(updates),
        "closed": sum(1 for update in updates if update["closed"]),
        "missing_prices": missing,
        "stale_sources": stale_sources,
        "updates": updates,
        "threshold_pct": threshold,
    }


def format_updates(result: dict[str, Any]) -> str:
    lines = []
    for update in sorted(result["updates"], key=lambda item: item["pnl_pct"] or 0, reverse=True):
        if update.get("expired"):
            verdict = "RIGHT" if (update.get("pnl_pct") or 0) > 0 else "WRONG"
            tag = f"EXPIRED ({verdict})"
        elif update["closed"]:
            tag = "CLOSED (WRONG)"
        elif update.get("stale_source"):
            # The provider offered an older session than the mark we already
            # hold. Keeping the newer mark is the correct answer, not a gap.
            tag = f"{update['kind'].upper()} · HELD (source behind)"
        elif not update.get("priced", True):
            stale = update.get("stale_days")
            tag = f"{update['kind'].upper()} · NO PRICE" + (f" ({stale}d stale)" if stale else "")
        else:
            tag = update["kind"].upper()
        price = update["price"]
        pnl = update["pnl_pct"]
        # An unjudged call has no contract to name: printing one would state a
        # decision nobody made.
        instrument = update.get("instrument")
        contract = str(instrument).upper() if instrument else "—"
        dte = update.get("days_to_expiry")
        contract += f" {dte:>3}d" if dte is not None else ""
        lines.append(
            f"  {update['ticker']:<6} {contract:<9} "
            f"entry={update['entry_price']:<8.2f} "
            f"now={'-' if price is None else format(price, '.2f'):<8} "
            f"pnl={'-' if pnl is None else format(pnl, '+.1f') + '%':<8} {tag}"
        )
    return "\n".join(lines) or "  (no open calls)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update prices for open lowcap calls")
    parser.add_argument("--config")
    parser.add_argument("--db", help="Override tracker.db_path")
    parser.add_argument("--prices-json", help="JSON mapping of ticker -> price (offline)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    db_path = args.db or resolve_path(config, "db_path")
    prices = json.loads(args.prices_json) if args.prices_json else None

    with CallDatabase(db_path) as db:
        result = update_open_calls(db, config, prices=prices)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return 0
    print(f"Priced {result['priced']} open call(s); closed {result['closed']}")
    print(format_updates(result))
    return 0


__all__ = ["fetch_prices", "update_open_calls", "format_updates", "pnl_pct"]

if __name__ == "__main__":
    sys.exit(main())
