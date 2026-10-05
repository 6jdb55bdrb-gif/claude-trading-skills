"""The untraded-quote guard belongs to the extended session only.

The guard exists because a thin microcap quotes PRE-MARKET with zero volume:
nobody traded there, so the mark may move but the stop must not act. Scoped too
widely it misfires. During REGULAR hours a five-minute bar can also report zero
volume — BIRD did at 11:33 on 5 October — but 3.37 was then a real last-traded
price from earlier in the session, not a quote. Deferring a stop on it would
hold a position open that should have closed, and BIRD was 8% from its stop.

So: outside regular hours, zero volume defers the stop. Inside regular hours,
the stop acts regardless of one quiet bar.
"""

from call_db import STATUS_OPEN, STATUS_STOPPED
from price_update import format_updates, update_open_calls

from conftest import review_payload


def _cfg(config, **over):
    return {
        **config,
        "tracker": {
            **config["tracker"],
            "trailing_stop_pct": 15.0,
            "trailing_stop_atr_mult": 1.5,
            "mark_extended_hours": True,
            "stop_on_untraded_extended": False,
            **over,
        },
    }


def _open(db, ticker="AAA", entry=3.66, atr=0.23):
    review = review_payload(ticker, entry=entry)
    review["hit"] = {"ticker": ticker, "atr": atr, "price": entry}
    return db.insert_call(
        review,
        run_id="r1",
        now="2026-10-01T15:00:00+00:00",
        allocation_usd=100.0,
        trail_floor_pct=15.0,
        trail_atr_mult=1.5,
    )


def _zero_volume_break(db, config, *, regular_hours):
    """A stop-breaching mark on a bar that reports no volume."""
    return update_open_calls(
        db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 3.66,
                "as_of": "2026-10-02",
                "extended_price": 2.80,
                "extended_as_of": "2026-10-05",
                "extended_volume": 0,
            }
        },
        today="2026-10-05",
        regular_hours=regular_hours,
    )


def test_in_regular_hours_a_quiet_bar_still_stops_the_call(tmp_db, config):
    """BIRD's case: 3.37 with no volume in the last 5 minutes is a real price."""
    call_id = _open(tmp_db)
    _zero_volume_break(tmp_db, config, regular_hours=True)
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


def test_outside_regular_hours_a_quiet_bar_defers_the_stop(tmp_db, config):
    """Pre-market: nobody traded there, so the stop waits."""
    call_id = _open(tmp_db)
    _zero_volume_break(tmp_db, config, regular_hours=False)
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["current_price"] == 2.80  # the mark still moved


def test_the_report_only_says_untraded_outside_regular_hours(tmp_db, config):
    _open(tmp_db)
    held = _zero_volume_break(tmp_db, config, regular_hours=False)
    assert "EXT (untraded)" in format_updates(held)


def test_the_report_does_not_say_untraded_during_the_session(tmp_db, config):
    _open(tmp_db, "BBB")
    result = update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "BBB": {
                "price": 3.66,
                "as_of": "2026-10-02",
                "extended_price": 3.50,
                "extended_as_of": "2026-10-05",
                "extended_volume": 0,
            }
        },
        today="2026-10-05",
        regular_hours=True,
    )
    text = format_updates(result)
    assert "EXT" in text
    assert "untraded" not in text


def test_a_traded_bar_stops_in_either_session(tmp_db, config):
    for ticker, regular in (("CCC", True), ("DDD", False)):
        call_id = _open(tmp_db, ticker)
        update_open_calls(
            tmp_db,
            _cfg(config),
            prices={
                ticker: {
                    "price": 3.66,
                    "as_of": "2026-10-02",
                    "extended_price": 2.80,
                    "extended_as_of": "2026-10-05",
                    "extended_volume": 9000,
                }
            },
            today="2026-10-05",
            regular_hours=regular,
        )
        assert tmp_db.call(call_id)["status"] == STATUS_STOPPED, ticker


def test_regular_hours_resolves_from_the_clock_when_not_passed(tmp_db, config):
    """Production passes nothing; the session must be derived, not assumed."""
    _open(tmp_db)
    result = update_open_calls(tmp_db, _cfg(config), prices={"AAA": 3.60}, today="2026-10-05")
    assert isinstance(result["regular_hours"], bool)
