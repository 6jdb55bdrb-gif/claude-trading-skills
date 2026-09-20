#!/usr/bin/env python3
"""Minimal, dependency-free US cash-session helper.

The tracker only needs two answers: *is today a trading day* (so screening can
be skipped on weekends and holidays) and *are we inside regular hours*. That is
deliberately narrower than the repository's shared exchange-calendar runtime,
which pins ``pandas-market-calendars``; this module stays standard-library only
so the 4-hour VPS timer never fails on a calendar dependency.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo


def market_timezone(config: dict[str, Any]) -> ZoneInfo:
    return ZoneInfo(config["market"].get("timezone", "America/New_York"))


def now_et(config: dict[str, Any]) -> datetime:
    return datetime.now(market_timezone(config))


def _holidays(config: dict[str, Any]) -> set[date]:
    holidays: set[date] = set()
    for raw in config["market"].get("holidays") or []:
        if isinstance(raw, date):
            holidays.add(raw)
            continue
        try:
            holidays.add(date.fromisoformat(str(raw)))
        except ValueError:
            continue
    return holidays


def is_trading_day(config: dict[str, Any], when: date) -> bool:
    """True when *when* is a weekday that is not a configured holiday."""
    if when.weekday() >= 5:
        return False
    return when not in _holidays(config)


def _parse_clock(value: str, fallback: time) -> time:
    try:
        hours, minutes = str(value).split(":")
        return time(int(hours), int(minutes))
    except (ValueError, AttributeError):
        return fallback


def session_state(config: dict[str, Any], moment: datetime | None = None) -> dict[str, Any]:
    """Classify *moment* (default: now, ET) for the screening decision.

    Returns ``{as_of, trading_day, regular_hours, screening_allowed, reason}``.
    """
    market = config["market"]
    moment = moment or now_et(config)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=market_timezone(config))
    else:
        moment = moment.astimezone(market_timezone(config))

    trading_day = is_trading_day(config, moment.date())
    open_at = _parse_clock(market.get("regular_open", "09:30"), time(9, 30))
    close_at = _parse_clock(market.get("regular_close", "16:00"), time(16, 0))
    regular = trading_day and open_at <= moment.time() <= close_at

    if not market.get("skip_screening_when_closed", True):
        allowed, reason = True, "screening forced on by configuration"
    elif not trading_day:
        allowed = False
        reason = (
            "weekend — US market closed"
            if moment.weekday() >= 5
            else "US market holiday — market closed"
        )
    elif regular:
        allowed, reason = True, "regular trading hours"
    elif market.get("allow_extended_hours", True):
        allowed, reason = True, "trading day, extended hours"
    else:
        allowed, reason = False, "outside regular hours and extended hours disabled"

    return {
        "as_of": moment.isoformat(timespec="seconds"),
        "trading_day": trading_day,
        "regular_hours": regular,
        "screening_allowed": allowed,
        "reason": reason,
    }
