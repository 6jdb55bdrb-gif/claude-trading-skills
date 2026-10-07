#!/usr/bin/env python3
"""The fixed stop loss: one line, set at entry, never moved.

This is deliberately a different instrument from the trailing stop already in
``call_db.apply_price``. The trailing stop ratchets with a high-water mark and
exists to ride a move; this one is a flat line under the entry price, used by
v2 of the screener and by the outcome tracker.

Two rules carry all the meaning:

* ``stop = entry_price x (1 - sl_pct/100)``, rounded to the cent — a price
  nobody can trade at is not a stop.
* The outcome tracker compares it to each day's **LOW**, not the close. A
  position that traded through its stop at 10am and closed above it was gone;
  scoring it on the close would flatter every result that follows.

Long only, so the stop is always below entry. Anything unusable — a missing
entry price, a percentage outside (0, 100) — yields ``None`` rather than an
invented level.
"""

from __future__ import annotations

from typing import Any

DEFAULT_SL_PCT = 20.0

# `sl_pct=None` has to mean "disabled" — that is what null in the config means —
# so "not supplied, fall back to the config" needs its own value. Without the
# sentinel one parameter carries both meanings and callers cannot disable it.
_UNSET = object()


def _number(value: Any) -> float | None:
    """A finite float, or None. Never raises on junk."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number or number in (float("inf"), float("-inf")) else number


def sl_pct(config: dict[str, Any] | None) -> float | None:
    """The configured stop distance in percent, or None when disabled."""
    if not config:
        return DEFAULT_SL_PCT
    raw = (config.get("tracker") or {}).get("sl_pct", DEFAULT_SL_PCT)
    number = _number(raw)
    return number if number is not None and 0 < number < 100 else None


def calculate_stop_loss(
    entry_price: Any,
    *,
    sl_pct: Any = _UNSET,
    config: dict[str, Any] | None = None,
) -> float | None:
    """The stop price for a long entry, or None when one cannot be derived.

    ``sl_pct`` wins over ``config``; omit it to take the config's value, or pass
    None explicitly to disable the stop.
    """
    if sl_pct is _UNSET:
        pct = globals()["sl_pct"](config) if config is not None else DEFAULT_SL_PCT
    else:
        pct = _number(sl_pct)
        if pct is None or not 0 < pct < 100:
            return None
    if pct is None:
        return None
    entry = _number(entry_price)
    if entry is None or entry <= 0:
        return None
    return round(entry * (1 - pct / 100.0), 2)


def stop_hit(*, low: Any, stop: Any) -> bool:
    """Did this session's low reach the stop?

    ``low <= stop`` counts: at the stop price the order fills, and treating the
    touch as a miss flatters the book. A missing low is not evidence of a
    stop-out, so it returns False.
    """
    stop_price = _number(stop)
    low_price = _number(low)
    if stop_price is None or low_price is None:
        return False
    return low_price <= stop_price
