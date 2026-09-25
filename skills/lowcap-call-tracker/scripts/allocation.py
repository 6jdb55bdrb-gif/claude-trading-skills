#!/usr/bin/env python3
"""What the account is actually doing: cash, positions, and what it is worth.

The tracker's PnL percentages say whether each call was right. This says what
they would have been worth. A fixed dollar slice goes into every call at entry
(``tracker.position_pct`` of ``tracker.account_size``), the position then moves
with the underlying, and whatever is not in a position is cash.

Three rules keep the number honest:

* **The slice is fixed at entry**, never rebalanced. A position that doubled is
  worth double; it does not quietly take more of the account.
* **A closed call returns its value to cash**, so a realized win or loss is
  spent or lost for good and cannot be marked again.
* **A voided call never touched the cash.** It could not have been executed, so
  no money was ever committed to it.
"""

from __future__ import annotations

from typing import Any

from call_db import STATUS_OPEN, STATUS_VOID, CallDatabase


def account_size(config: dict[str, Any]) -> float:
    return float(config["tracker"].get("account_size", 1000.0) or 0.0)


def position_pct(config: dict[str, Any]) -> float:
    return float(config["tracker"].get("position_pct", 10.0) or 0.0)


def slice_usd(config: dict[str, Any], *, cash_available: float) -> float | None:
    """The dollars the next call gets, or None when there is nothing left.

    The last position in a full book is whatever cash remains, not a full
    slice: the account cannot commit money it does not have.
    """
    if cash_available <= 0:
        return None
    full = round(account_size(config) * position_pct(config) / 100.0, 2)
    if full <= 0:
        return None
    return round(min(full, cash_available), 2)


def _value(allocation: float, pnl_pct: float | None) -> float:
    return round(allocation * (1.0 + (pnl_pct or 0.0) / 100.0), 2)


def portfolio_state(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    """Cash, open positions and total account value."""
    account = account_size(config)
    rows = db.all_calls()

    positions: list[dict[str, Any]] = []
    allocated = 0.0
    positions_value = 0.0
    realized = 0.0
    unallocated: list[str] = []

    for row in rows:
        if row["status"] == STATUS_VOID:
            continue  # never executed, so never funded
        allocation = row["allocation_usd"]
        if not allocation:
            # Called before the account existed, or deliberately unfunded. It is
            # named rather than valued: inventing a size would invent a return.
            unallocated.append(row["ticker"])
            continue
        allocation = float(allocation)
        value = _value(allocation, row["pnl_pct"])
        if row["status"] == STATUS_OPEN:
            allocated += allocation
            positions_value += value
            positions.append(
                {
                    "ticker": row["ticker"],
                    "allocation_usd": round(allocation, 2),
                    "value_usd": value,
                    "pnl_usd": round(value - allocation, 2),
                    "pnl_pct": row["pnl_pct"],
                }
            )
        else:
            realized += value - allocation

    cash = round(account - allocated + realized, 2)
    portfolio_value = round(cash + positions_value, 2)
    return {
        "account_usd": round(account, 2),
        "position_pct": position_pct(config),
        "cash_usd": cash,
        "allocated_usd": round(allocated, 2),
        "allocated_pct": round(allocated / account * 100.0, 1) if account else 0.0,
        "positions_value_usd": round(positions_value, 2),
        "portfolio_value_usd": portfolio_value,
        "realized_usd": round(realized, 2),
        "total_return_pct": round((portfolio_value - account) / account * 100.0, 2)
        if account
        else 0.0,
        "positions": positions,
        "unallocated_calls": unallocated,
    }


def money(value: float | None) -> str:
    """$1,020.00 — or an em dash. Never 'None'."""
    if value is None:
        return "—"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"
