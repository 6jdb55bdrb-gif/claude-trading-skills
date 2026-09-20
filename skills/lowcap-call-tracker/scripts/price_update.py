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

from config import load_config, resolve_path

try:
    import yfinance

    HAS_YFINANCE = True
except ImportError:  # pragma: no cover - offline installs pass --prices-json
    HAS_YFINANCE = False


def _age_days(stamp: Any, now: datetime) -> int | None:
    """Whole days between an ISO timestamp and *now*; None when unparseable."""
    if not stamp:
        return None
    try:
        moment = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0, (now - moment).days)


def fetch_prices(tickers: list[str]) -> dict[str, float]:
    """Return {ticker: last price}; missing tickers are simply absent."""
    if not tickers or not HAS_YFINANCE:
        return {}
    prices: dict[str, float] = {}
    try:
        data = yfinance.download(
            tickers=" ".join(sorted(set(tickers))),
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
        for ticker in set(tickers):
            try:
                column = data[ticker]["Close"] if len(set(tickers)) > 1 else data["Close"]
                series = column.dropna()
                if len(series):
                    prices[ticker] = float(series.iloc[-1])
            except (KeyError, IndexError, TypeError, AttributeError):
                continue

    missing = [ticker for ticker in set(tickers) if ticker not in prices]
    for ticker in missing:  # pragma: no cover - per-ticker fallback
        try:
            series = yfinance.Ticker(ticker).history(period="5d")["Close"].dropna()
            if len(series):
                prices[ticker] = float(series.iloc[-1])
        except Exception:
            continue
    return prices


def update_open_calls(
    db: CallDatabase,
    config: dict[str, Any],
    *,
    prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Price every open call, apply the close rule, and summarize the result."""
    threshold = float(config["tracker"]["close_threshold_pct"])
    open_calls = db.open_calls()
    tickers = [row["ticker"] for row in open_calls]
    # An explicitly empty mapping means "offline, no prices" — not "go fetch".
    resolved = dict(prices) if prices is not None else fetch_prices(tickers)

    updates: list[dict[str, Any]] = []
    missing: list[str] = []
    now = datetime.now(timezone.utc)
    for row in open_calls:
        price = resolved.get(row["ticker"])
        common = {
            "direction": row["direction"],
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
            missing.append(row["ticker"])
            updates.append(
                {
                    "call_id": row["id"],
                    "ticker": row["ticker"],
                    "price": row["current_price"],
                    "pnl_pct": row["pnl_pct"],
                    "closed": False,
                    "priced": False,
                    "last_price_at": row["last_price_at"],
                    "stale_days": _age_days(row["last_price_at"], now),
                    **common,
                }
            )
            continue
        result = db.apply_price(row["id"], float(price), close_threshold_pct=threshold)
        result.update({"priced": True, "stale_days": 0, **common})
        updates.append(result)

    return {
        "priced": sum(1 for update in updates if update["priced"]),
        "open": len(updates),
        "closed": sum(1 for update in updates if update["closed"]),
        "missing_prices": missing,
        "updates": updates,
        "threshold_pct": threshold,
    }


def format_updates(result: dict[str, Any]) -> str:
    lines = []
    for update in sorted(result["updates"], key=lambda item: item["pnl_pct"] or 0, reverse=True):
        if update["closed"]:
            tag = "CLOSED (WRONG)"
        elif not update.get("priced", True):
            stale = update.get("stale_days")
            tag = f"{update['kind'].upper()} · NO PRICE" + (f" ({stale}d stale)" if stale else "")
        else:
            tag = update["kind"].upper()
        price = update["price"]
        pnl = update["pnl_pct"]
        lines.append(
            f"  {update['ticker']:<6} {update['direction']:<5} "
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
