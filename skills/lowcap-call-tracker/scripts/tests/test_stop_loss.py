"""The fixed stop loss used by v2, and how the outcome tracker reads it.

A fixed stop is a different instrument from the trailing stop already in the
tracker: it never moves, it is quoted in the TAKE message, and the outcome
tracker checks each day's LOW against it rather than the close. Checking the
close would let a position that traded through the stop intraday look like a
survivor, which is the whole failure this is meant to avoid.
"""

import pytest
from stop_loss import calculate_stop_loss, sl_pct, stop_hit

# --- calculate_stop_loss ---------------------------------------------------


@pytest.mark.parametrize(
    "entry, pct, expected",
    [
        (10.00, 20.0, 8.00),
        (3.66, 20.0, 2.93),  # BIRD's entry
        (4.57, 20.0, 3.66),  # SDEV's
        (18.65, 20.0, 14.92),
        (1.04, 20.0, 0.83),
        (10.00, 10.0, 9.00),  # a different pct
        (10.00, 50.0, 5.00),
    ],
)
def test_the_stop_is_the_entry_less_the_configured_percent(entry, pct, expected):
    assert calculate_stop_loss(entry, sl_pct=pct) == expected


def test_the_default_percent_comes_from_the_config(config):
    """The shipped stop, asserted in one place. Widened to 30% on 2026-10-08."""
    assert sl_pct(config) == 30.0
    assert calculate_stop_loss(10.0, config=config) == 7.00


def test_the_stop_is_rounded_to_the_cent():
    """A price nobody can trade at is not a stop."""
    assert calculate_stop_loss(3.333, sl_pct=20.0) == 2.67


def test_the_stop_is_always_below_entry_because_the_book_is_long_only():
    for entry in (0.5, 1.0, 7.58, 100.0):
        assert calculate_stop_loss(entry, sl_pct=20.0) < entry


@pytest.mark.parametrize("entry", [0, -1, None, "", "abc", float("nan")])
def test_an_unusable_entry_price_yields_no_stop(entry):
    """Never invent a stop from a price we do not have."""
    assert calculate_stop_loss(entry, sl_pct=20.0) is None


def test_a_disabled_percent_yields_no_stop():
    assert calculate_stop_loss(10.0, sl_pct=None) is None


@pytest.mark.parametrize("pct", [0, -5, 100, 150])
def test_a_percent_outside_the_open_interval_yields_no_stop(pct):
    """0 would stop at entry and 100 would stop at zero; neither is a stop."""
    assert calculate_stop_loss(10.0, sl_pct=pct) is None


# --- stop_hit: the outcome tracker's daily check --------------------------


def test_the_normal_case_a_low_above_the_stop_is_not_a_hit(config):
    assert stop_hit(low=8.50, stop=8.00) is False


def test_a_low_that_pierces_the_stop_intraday_is_a_hit(config):
    """The close is irrelevant: the position was gone before it printed."""
    assert stop_hit(low=7.40, stop=8.00) is True


def test_a_low_exactly_on_the_stop_is_a_hit(config):
    """At the stop price the order fills. Treating it as a miss flatters the book."""
    assert stop_hit(low=8.00, stop=8.00) is True


def test_no_stop_means_no_hit(config):
    assert stop_hit(low=0.01, stop=None) is False


def test_a_missing_low_is_not_a_hit(config):
    """Absent data is not evidence of a stop-out."""
    assert stop_hit(low=None, stop=8.00) is False


def test_the_bird_case_end_to_end(config):
    """BIRD: entry 3.66, so the configured 30% stop sits at 2.56.

    Its low was 3.12 and it closed on the TRAILING stop at -16.4%, so the
    fixed line would not have fired at 20% either. That is the division of
    labour: the trail takes a call out on a reversal, the fixed stop is the
    floor under a collapse.
    """
    stop = calculate_stop_loss(3.66, config=config)
    assert stop == 2.56
    assert stop_hit(low=3.1217, stop=stop) is False
    assert stop_hit(low=2.50, stop=stop) is True
