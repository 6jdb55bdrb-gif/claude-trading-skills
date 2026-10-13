#!/usr/bin/env python3
"""Capital rotation: close the worst position to fund a better call.

The book used to run two ledgers side by side. The screener kept calling, and
once the account was fully committed the new calls were logged with no money
behind them — tracked, unvalued, and indistinguishable in the report from a
position the account actually held. Six of seventeen open calls were in that
state. The operator's instruction was to stop running the dollars in parallel
with the calls: "the money should rotate — positions should be closed to get
the cash to put into other calls".

So the account now behaves like an account. A new call that cannot be funded
either displaces an existing position or is not made.

Every rule here is a brake, because this spends real money on a screener hit:

* **Only a TAKE may displace.** A SKIP is a call the Judge refused; it has no
  claim on capital that is already committed.
* **A winner is never displaced.** Selling what is working to buy what is new
  is a machine for turning a good book into a bad one. Only a position that is
  actually down is a rotation candidate, and the worst one goes first.
* **The newcomer must beat it by a margin** (``min_confidence_edge``). 75
  against 70 is noise; acting on noise would churn the book every scan.
* **A run may only rotate so many times** (``max_per_run``), so a single
  pre-market batch cannot recycle the entire account before the open.
* **What is freed is the position's VALUE, not its allocation.** $100 put into
  a name now 30% down is $70 of cash. Freeing the allocation would invent $30
  that was lost.

A rotation is recorded on both sides: the closed call's ``close_reason`` names
the call it funded, and the run report names the pair.
"""

from __future__ import annotations

from typing import Any

from allocation import full_slice_usd, portfolio_state
from call_db import KIND_ACTIVE, STATUS_OPEN, CallDatabase

# Defaults applied when `tracker.rotation` is absent or partial. They are the
# conservative end of every choice above: on, but only for a reviewed TAKE
# with a real edge over a losing position.
ROTATION_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "require_take": True,
    "protect_winners": True,
    "max_displace_pnl_pct": 0.0,
    "min_confidence_edge": 10,
    "max_per_run": 3,
}


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def rotation_settings(config: dict[str, Any]) -> dict[str, Any]:
    """The rotation policy, with every missing key defaulted."""
    raw = (config.get("tracker") or {}).get("rotation") or {}
    settings = {**ROTATION_DEFAULTS}
    if isinstance(raw, dict):
        settings.update({key: raw[key] for key in raw if key in ROTATION_DEFAULTS})
    return settings


def rotation_enabled(config: dict[str, Any]) -> bool:
    return bool(rotation_settings(config)["enabled"])


def capital_gated(config: dict[str, Any]) -> bool:
    """True when a call that cannot be funded is not made at all.

    The alternative — recording it with no allocation — is the parallel book
    the operator objected to. Left on; set ``tracker.capital_gated: false`` to
    go back to logging an unfunded call as an observation.
    """
    raw = (config.get("tracker") or {}).get("capital_gated", True)
    return raw is not False


def displaceable(db: CallDatabase, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Open, funded, losing positions — worst first.

    Worst first because the cheapest capital to recycle is the capital doing
    the least: a position already down is the one whose thesis is furthest
    from working.
    """
    settings = rotation_settings(config)
    limit = _number(settings.get("max_displace_pnl_pct"))
    limit = 0.0 if limit is None else limit
    if settings.get("protect_winners"):
        # A positive threshold would make "protect winners" mean "displace the
        # small winners", which is not what the words say.
        limit = min(limit, 0.0)

    rows: list[dict[str, Any]] = []
    for row in db.open_calls():
        allocation = _number(row["allocation_usd"])
        if not allocation:
            continue  # never spent anything, so closing it frees nothing
        pnl = _number(row["pnl_pct"])
        if pnl is None or pnl >= limit:
            continue
        rows.append(
            {
                "call_id": row["id"],
                "ticker": row["ticker"],
                "kind": row["kind"],
                "pnl_pct": pnl,
                "confidence": _number(row["confidence"]),
                "allocation_usd": round(allocation, 2),
                "value_usd": round(allocation * (1.0 + pnl / 100.0), 2),
            }
        )
    rows.sort(key=lambda entry: (entry["pnl_pct"], entry["ticker"]))
    return rows


def pick_displacement(
    review: dict[str, Any],
    candidates: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, Any] | None:
    """The position *review* is allowed to displace, or None."""
    if not candidates:
        return None
    if settings.get("require_take") and review.get("decision") != "TAKE":
        return None
    confidence = _number(review.get("confidence"))
    if confidence is None:
        # An unjudged hit cannot be compared, and "cannot be compared" must
        # not resolve to "wins".
        return None
    edge = _number(settings.get("min_confidence_edge"))
    edge = 0.0 if edge is None else edge
    ticker = str(review.get("ticker", "")).upper()
    for candidate in candidates:
        if candidate["ticker"].upper() == ticker:
            continue  # the same name open twice is a duplicate, not a rotation
        if confidence - (candidate["confidence"] or 0.0) >= edge:
            return candidate
    return None


def rotate_for(
    db: CallDatabase,
    config: dict[str, Any],
    *,
    review: dict[str, Any],
    run_id: str,
    budget: dict[str, int] | None = None,
    now: str | None = None,
) -> list[dict[str, Any]]:
    """Free cash for *review* by closing losing positions. Returns what closed.

    Stops as soon as a full slice is available, when no eligible position is
    left, or when the run's rotation budget is spent. Returns an empty list
    when there is already cash, which is the common case.
    """
    settings = rotation_settings(config)
    if not settings["enabled"]:
        return []
    allowed = _number(settings.get("max_per_run"))
    allowed = 0 if allowed is None else int(allowed)
    budget = budget if budget is not None else {"used": 0}

    needed = full_slice_usd(config)
    if needed <= 0:
        return []

    rotated: list[dict[str, Any]] = []
    while budget.get("used", 0) < allowed:
        cash = portfolio_state(db, config)["cash_usd"]
        if cash >= needed:
            break
        candidate = pick_displacement(review, displaceable(db, config), settings)
        if candidate is None:
            break
        reason = (
            f"rotated out to fund {review['ticker']} "
            f"(conf {int(_number(review.get('confidence')) or 0)} vs "
            f"{int(candidate['confidence'] or 0)}, this position {candidate['pnl_pct']:+.2f}%)"
        )
        db.close_call(candidate["call_id"], reason=reason, now=now)
        budget["used"] = budget.get("used", 0) + 1
        rotated.append(
            {
                "call_id": candidate["call_id"],
                "ticker": candidate["ticker"],
                "kind": candidate["kind"],
                "pnl_pct": candidate["pnl_pct"],
                "allocation_usd": candidate["allocation_usd"],
                "freed_usd": candidate["value_usd"],
                "for_ticker": review["ticker"],
                "for_confidence": _number(review.get("confidence")),
                "run_id": run_id,
                "was_take": candidate["kind"] == KIND_ACTIVE,
            }
        )
    return rotated


def format_rotations(rotations: list[dict[str, Any]]) -> list[str]:
    """Report lines, one per rotation. The displaced side is named first."""
    lines = []
    for entry in rotations:
        lines.append(
            f"  {entry['ticker']:<6} closed {entry['pnl_pct']:+7.2f}% "
            f"→ ${entry['freed_usd']:,.2f} into {entry['for_ticker']}"
            + ("  (was a TAKE)" if entry["was_take"] else "")
        )
    return lines


__all__ = [
    "ROTATION_DEFAULTS",
    "capital_gated",
    "displaceable",
    "format_rotations",
    "pick_displacement",
    "rotate_for",
    "rotation_enabled",
    "rotation_settings",
    "STATUS_OPEN",
]
