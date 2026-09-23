"""Extended hours have bounds; the middle of the night is not one of them."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from market_hours import session_state

ET = ZoneInfo("America/New_York")


def _at(hour, minute=0, day=23):
    # 2026-09-23 is a Wednesday.
    return datetime(2026, 9, day, hour, minute, tzinfo=ET)


@pytest.mark.parametrize(
    ("moment", "allowed", "fragment"),
    [
        (_at(1, 13), False, "overnight"),  # the run that exposed this
        (_at(3, 59), False, "overnight"),
        (_at(4, 0), True, "extended"),  # pre-market opens
        (_at(9, 29), True, "extended"),
        (_at(9, 30), True, "regular"),
        (_at(16, 0), True, "regular"),
        (_at(16, 1), True, "extended"),  # after-hours
        (_at(20, 0), True, "extended"),
        (_at(20, 1), False, "overnight"),
        (_at(23, 59), False, "overnight"),
    ],
)
def test_screening_follows_the_real_session_bounds(config, moment, allowed, fragment):
    state = session_state(config, moment)
    assert state["screening_allowed"] is allowed
    assert fragment in state["reason"]


def test_a_weekend_still_reads_as_a_weekend(config):
    state = session_state(config, _at(12, 0, day=26))  # Saturday
    assert state["screening_allowed"] is False
    assert "weekend" in state["reason"]


def test_disabling_extended_hours_still_allows_regular(config):
    config = {**config, "market": {**config["market"], "allow_extended_hours": False}}
    assert session_state(config, _at(11, 0))["screening_allowed"] is True
    assert session_state(config, _at(5, 0))["screening_allowed"] is False


def test_forcing_screening_on_overrides_the_clock(config):
    config = {**config, "market": {**config["market"], "skip_screening_when_closed": False}}
    assert session_state(config, _at(1, 13))["screening_allowed"] is True
