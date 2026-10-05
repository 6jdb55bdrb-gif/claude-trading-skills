#!/usr/bin/env python3
"""What the account is actually doing: cash, positions, and what it is worth.

The tracker's PnL percentages say whether each call was right. This says what
they would have been worth. A fixed dollar slice goes into every call at entry
(``tracker.position_pct`` of ``tracker.account_size``), the position then moves
with the underlying, and whatever is not in a position is cash.

Two books are kept, and WHICH ONE IS THE ACCOUNT is the operator's call, set by
``tracker.account_funds``:

* ``all`` (the default) — every call the screener surfaced is funded, whatever
  the Judge said. This is the operator's actual behaviour: they take the hits.
* ``take_only`` — only calls the Judge said TAKE. What following the Judge
  would have returned.

``portfolio_state`` is whichever of those the setting names; ``take_only_state``
is always the TAKE-only figure, because the gap between the two is the only
thing that prices the Judge's selectivity.

I originally hard-coded the account to TAKE-only, on the assumption that nobody
would buy a call the Judge rejected. That was wrong, and it understated the
account badly: on the first eleven calls TAKE-only read -1.90% while every-call
read +21.38%, and almost all of that difference is one SKIP that ran (SDEV
+175.8%). Do not re-derive the account from a verdict again — ask.

Four rules keep the numbers honest:

* **The slice is fixed at entry**, never rebalanced. A position that doubled is
  worth double; it does not quietly take more of the account.
* **A closed call returns its value to cash**, so a realized win or loss is
  spent or lost for good and cannot be marked again.
* **A voided call never touched the cash.** It could not have been executed, so
  no money was ever committed to it.
* **Only a funded call spends the account's cash.** Which calls those are
  follows ``tracker.account_funds``, so the cash line always matches the book
  it belongs to.
"""

from __future__ import annotations

from typing import Any

from call_db import KIND_ACTIVE, STATUS_OPEN, STATUS_VOID, CallDatabase


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


def account_funds_all(config: dict[str, Any]) -> bool:
    """True when the account funds every call, not just the TAKEs.

    Anything other than an explicit ``take_only`` funds everything: a typo in
    this setting must not silently shrink the account to a single call.
    """
    raw = str(config["tracker"].get("account_funds", "all") or "all").strip().lower()
    return raw != "take_only"


def portfolio_state(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    """The account: cash, open positions and value, per ``account_funds``."""
    return _book(db, config, taken_only=not account_funds_all(config))


def take_only_state(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    """The same account restricted to TAKE calls — the Judge's scorecard.

    Always computed, whichever book the account uses, because the gap between
    the two is what says whether the Judge is adding anything.
    """
    return _book(db, config, taken_only=True)


def every_call_state(db: CallDatabase, config: dict[str, Any]) -> dict[str, Any]:
    """The same account over every call, whatever the verdict."""
    return _book(db, config, taken_only=False)


# Kept so older callers and reports do not break on the rename.
shadow_state = every_call_state


def _book(db: CallDatabase, config: dict[str, Any], *, taken_only: bool) -> dict[str, Any]:
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
        if taken_only and row["kind"] != KIND_ACTIVE:
            # TAKE-only view: a shadow or unjudged call is left out, so this
            # figure answers "what would following the Judge have returned".
            continue
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
