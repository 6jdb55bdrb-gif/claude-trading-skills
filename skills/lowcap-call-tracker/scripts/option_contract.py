#!/usr/bin/env python3
"""Contract selection: turn a directional read into a call or put with an expiry.

PnL is measured on the UNDERLYING (the screened universe is low-float micro caps,
which have no listed options market), so the strike is recorded for the record
rather than priced. What matters for the tracker is the instrument and the
expiration date: a call closes when its contract expires, and nothing else
closes it.

Expiry horizon follows the setup, per the Risk Manager's own judgement:

* a fade of a climactic move needs the least time (``options.fade_dte``),
* a catalyst-driven trend needs the most (``options.catalyst_dte``),
* anything else takes ``options.default_dte``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

FRIDAY = 4  # date.weekday()


def _options_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return ((config or {}).get("tracker") or {}).get("options") or {}


def next_friday(when: date) -> date:
    """The Friday on or after *when* — US options expire on Fridays."""
    return when + timedelta(days=(FRIDAY - when.weekday()) % 7)


def choose_expiry(
    *,
    config: dict[str, Any] | None = None,
    as_of: date | None = None,
    setup: str = "default",
) -> tuple[str, int]:
    """Return ``(expiry_date_iso, days_to_expiration)`` for a *setup*.

    ``setup`` is ``fade`` (climactic reversal), ``catalyst`` (news-driven trend)
    or ``default``.
    """
    options = _options_config(config)
    horizons = {
        "fade": int(options.get("fade_dte", 21)),
        "catalyst": int(options.get("catalyst_dte", 45)),
        "default": int(options.get("default_dte", 30)),
    }
    as_of = as_of or date.today()
    target = as_of + timedelta(days=horizons.get(setup, horizons["default"]))
    if options.get("snap_to_friday", True):
        target = next_friday(target)
    return target.isoformat(), (target - as_of).days


def choose_strike(price: float | None, instrument: str) -> float | None:
    """Nearest listed-style strike to the money.

    Strike increments follow the price: $0.50 under $10, $1 under $25, $5 above.
    A call rounds up and a put rounds down, so the contract is the nearest strike
    the trade would actually reach for.
    """
    if not price or price <= 0:
        return None
    increment = 0.5 if price < 10 else (1.0 if price < 25 else 5.0)
    steps = price / increment
    step = int(steps) + 1 if instrument == "call" and steps % 1 else int(steps)
    if instrument == "put" and steps % 1:
        step = int(steps)
    return round(max(increment, step * increment), 2)


def classify_setup(
    *,
    technician: dict[str, Any] | None,
    researcher: dict[str, Any] | None,
    skeptic: dict[str, Any] | None,
) -> str:
    """Name the setup so the expiry horizon fits what the trade needs."""
    technician = technician or {}
    researcher = researcher or {}
    skeptic = skeptic or {}
    extension = technician.get("extension_pct_sma20")
    climactic = technician.get("volume_pattern") == "climactic"
    severe = float(skeptic.get("score") or 0) >= 7
    if climactic or (extension is not None and float(extension) > 50 and severe):
        return "fade"
    catalyst = str(researcher.get("catalyst_type") or "none_found")
    if catalyst not in {"none_found", "retail_hype"} and float(researcher.get("score") or 0) >= 6:
        return "catalyst"
    return "default"


def build_contract(
    *,
    instrument: str,
    price: float | None,
    config: dict[str, Any] | None = None,
    technician: dict[str, Any] | None = None,
    researcher: dict[str, Any] | None = None,
    skeptic: dict[str, Any] | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Full contract for a call: instrument, strike, expiry, horizon rationale."""
    setup = classify_setup(technician=technician, researcher=researcher, skeptic=skeptic)
    expiry, dte = choose_expiry(config=config, as_of=as_of, setup=setup)
    return {
        "instrument": instrument,
        "strike": choose_strike(price, instrument),
        "expiry_date": expiry,
        "dte": dte,
        "expiry_setup": setup,
    }


def days_to_expiry(expiry: str | None, as_of: date | None = None) -> int | None:
    """Whole days until *expiry*; negative once it has passed."""
    if not expiry:
        return None
    try:
        target = date.fromisoformat(str(expiry)[:10])
    except ValueError:
        return None
    return (target - (as_of or date.today())).days


def is_expired(expiry: str | None, as_of: date | None = None) -> bool:
    """True when the contract's expiration date has passed."""
    remaining = days_to_expiry(expiry, as_of)
    return remaining is not None and remaining < 0


def parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None
