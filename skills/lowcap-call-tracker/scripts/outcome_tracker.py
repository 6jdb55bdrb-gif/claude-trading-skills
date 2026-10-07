#!/usr/bin/env python3
"""Fill in what every judged call actually did, and score the Judge on it.

The five roles produce an opinion; this module produces the record that opinion
is answerable to. Every call is measured the same way, TAKE and SKIP alike,
because a Judge is only worth keeping if the names it refused did worse than
the names it took.

The measurement is deliberately mechanical:

* returns at +1, +3 and +5 *sessions* after the call (the call's own session is
  day zero — the entry is the price at scan, so that day's close is already a
  result, not a starting point);
* one fixed stop line per call (``calls.sl_price``), checked against each
  session's LOW, because a stop is hit intraday and not at the close;
* a stopped call is out at the stop. Horizons that elapsed before the stop keep
  their real closes; the horizon the stop fired in and every later one record
  the stop's return, since that is what the position returned. No price after
  the stop is read again.

CLI:
    python3 outcome_tracker.py --fill
    python3 outcome_tracker.py --report
    python3 outcome_tracker.py --fill --report --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from typing import Any

from call_db import CallDatabase

from config import load_config, load_dotenv, resolve_path

HORIZONS = (1, 3, 5)
RETURN_COLUMNS = {horizon: f"ret_{horizon}d" for horizon in HORIZONS}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _day(stamp: Any) -> str | None:
    """The ``YYYY-MM-DD`` part of a date or timestamp, or None."""
    if not stamp:
        return None
    text = str(stamp).strip()
    if not text:
        return None
    return text.split("T")[0].split(" ")[0]


def _percent(entry: float, price: float, direction: str) -> float:
    move = (price / entry - 1.0) * 100.0
    return round(-move if direction == "short" else move, 2)


def evaluate_outcome(
    *,
    entry: Any,
    sl_price: Any = None,
    bars: list[dict[str, Any]],
    direction: str = "long",
    horizons: tuple[int, ...] = HORIZONS,
) -> dict[str, Any]:
    """Score one call against the sessions that followed it.

    *bars* are ``{"date", "low", "close"}`` rows for the sessions after the
    call, oldest first; the caller is responsible for excluding the call's own
    session and any bar that is still forming.
    """
    out: dict[str, Any] = {f"ret_{horizon}d": None for horizon in horizons} | {
        "stopped_out": False,
        "stopped_out_date": None,
        "complete": False,
    }
    entry_price = _number(entry)
    if not entry_price or entry_price <= 0:
        return out

    stop = _number(sl_price)
    # A short has no fixed stop line: calculate_stop_loss subtracts from the
    # entry, which is only a stop for a long. Nothing is invented here.
    if direction == "short":
        stop = None
    stop_return = _percent(entry_price, stop, direction) if stop else None

    for index, bar in enumerate(bars, start=1):
        low = _number(bar.get("low"))
        close = _number(bar.get("close"))
        if stop and low is not None and low <= stop:
            out["stopped_out"] = True
            out["stopped_out_date"] = _day(bar.get("date"))
            # Everything from this session on is the stop, including horizons
            # that have not elapsed yet: the position is closed, so no later
            # price can change what it returned.
            for horizon in horizons:
                if horizon >= index:
                    out[f"ret_{horizon}d"] = stop_return
            out["complete"] = True
            return out
        if index in horizons and close is not None:
            out[f"ret_{index}d"] = _percent(entry_price, close, direction)

    out["complete"] = all(out[f"ret_{horizon}d"] is not None for horizon in horizons)
    return out


def settled_return(row: Any) -> float | None:
    """The longest horizon that has elapsed, which is what a call is judged on.

    A three-day-old call is not excluded from the scorecard for lacking a
    five-day number; it is scored on what it has.
    """
    for horizon in sorted(HORIZONS, reverse=True):
        value = _number(_get(row, f"ret_{horizon}d"))
        if value is not None:
            return value
    return None


def _get(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def pending_calls(db: CallDatabase) -> list[dict[str, Any]]:
    """Calls still owed a measurement: unfinished and not already stopped out."""
    cursor = db.conn.execute(
        """
        SELECT id, ticker, call_date, entry_price, sl_price, direction,
               screener_version, screen_variant, judge_decision, confidence,
               researcher_score, ret_1d, ret_3d, ret_5d, stopped_out
          FROM calls
         WHERE COALESCE(stopped_out, 0) = 0
           AND (ret_1d IS NULL OR ret_3d IS NULL OR ret_5d IS NULL)
         ORDER BY call_date, id
        """
    )
    return [dict(row) for row in cursor]


def fetch_bars(tickers: list[str], *, start: str, verbose: bool = False) -> dict[str, list[dict]]:
    """Daily ``{"date", "low", "close"}`` rows per ticker from *start*.

    yfinance is the same free source the price update uses. A provider failure
    returns nothing for that ticker rather than a guess; the call stays pending
    and the next run tries again.
    """
    try:
        import yfinance
    except ImportError:  # pragma: no cover - requirements.txt declares it
        print(
            "ERROR: yfinance is required to fill outcomes. "
            "Install it with: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return {}
    if not tickers:
        return {}

    out: dict[str, list[dict[str, Any]]] = {}
    for ticker in sorted(set(tickers)):
        try:
            frame = yfinance.Ticker(ticker).history(start=start, interval="1d", auto_adjust=False)
        except Exception as exc:  # pragma: no cover - network/provider failure
            if verbose:
                print(f"  {ticker}: history unavailable ({exc})", file=sys.stderr)
            continue
        rows = []
        for index, row in frame.iterrows():
            rows.append(
                {
                    "date": str(index.date()),
                    "low": _number(row.get("Low")),
                    "close": _number(row.get("Close")),
                }
            )
        if rows:
            out[ticker] = rows
    return out


def sessions_after(
    bars: list[dict[str, Any]], *, call_date: str | None, as_of: str
) -> list[dict[str, Any]]:
    """The usable sessions strictly after *call_date* and before *as_of*.

    *as_of* is excluded because its bar is still forming: mid-session the close
    is not a close, and a wrong +1d return would never be revisited.
    """
    rows = []
    for bar in bars:
        day = _day(bar.get("date"))
        if not day or (call_date and day <= call_date) or day >= as_of:
            continue
        rows.append(bar)
    return sorted(rows, key=lambda bar: _day(bar.get("date")) or "")


def fill_outcomes(
    db: CallDatabase,
    config: dict[str, Any],
    *,
    bars: dict[str, list[dict[str, Any]]] | None = None,
    as_of: str | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Measure every pending call. *bars* bypasses the network for tests."""
    today = as_of or date.today().isoformat()
    pending = pending_calls(db)
    result: dict[str, Any] = {
        "as_of": today,
        "pending": len(pending),
        "updated": 0,
        "stopped": 0,
        "missing": [],
    }
    if not pending:
        return result

    if bars is None:
        earliest = min(_day(row["call_date"]) or today for row in pending)
        bars = fetch_bars([row["ticker"] for row in pending], start=earliest, verbose=verbose)

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    missing: list[str] = []
    for row in pending:
        ticker = row["ticker"]
        series = bars.get(ticker)
        if not series:
            if ticker not in missing:
                missing.append(ticker)
            continue
        usable = sessions_after(series, call_date=_day(row["call_date"]), as_of=today)
        outcome = evaluate_outcome(
            entry=row["entry_price"],
            sl_price=row["sl_price"],
            bars=usable,
            direction=str(row["direction"] or "long"),
        )
        changed = {
            column: outcome[column]
            for horizon, column in RETURN_COLUMNS.items()
            if outcome[column] is not None and _number(row.get(column)) is None
        }
        if not changed and not outcome["stopped_out"]:
            continue
        db.conn.execute(
            """
            UPDATE calls
               SET ret_1d = COALESCE(?, ret_1d),
                   ret_3d = COALESCE(?, ret_3d),
                   ret_5d = COALESCE(?, ret_5d),
                   stopped_out = ?,
                   stopped_out_date = ?,
                   outcome_updated_at = ?
             WHERE id = ?
            """,
            (
                outcome["ret_1d"],
                outcome["ret_3d"],
                outcome["ret_5d"],
                1 if outcome["stopped_out"] else 0,
                outcome["stopped_out_date"],
                stamp,
                row["id"],
            ),
        )
        result["updated"] += 1
        if outcome["stopped_out"]:
            result["stopped"] += 1
        if verbose:
            print(
                f"  {ticker:<6} 1d={outcome['ret_1d']} 3d={outcome['ret_3d']} "
                f"5d={outcome['ret_5d']}"
                + (f"  STOPPED {outcome['stopped_out_date']}" if outcome["stopped_out"] else "")
            )
    db.conn.commit()
    result["missing"] = missing
    return result


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Fill and report call outcomes")
    parser.add_argument("--config")
    parser.add_argument("--db")
    parser.add_argument("--fill", action="store_true", help="Fetch prices and fill returns")
    parser.add_argument("--as-of", help="Treat this YYYY-MM-DD as today (replay)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    with CallDatabase(args.db or resolve_path(config, "db_path")) as db:
        filled = (
            fill_outcomes(db, config, as_of=args.as_of, verbose=args.verbose) if args.fill else None
        )

    if args.json:
        print(json.dumps({"fill": filled}, indent=2, default=str))
    elif filled:
        print(
            f"outcomes: {filled['updated']} updated of {filled['pending']} pending "
            f"({filled['stopped']} stopped out)"
            + (f"; no prices for {', '.join(filled['missing'])}" if filled["missing"] else "")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
