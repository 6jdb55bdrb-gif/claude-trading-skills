"""An untraded quote must not SHIELD a position from a traded close.

The rule that a zero-volume extended print may move the mark but not close a
position is right, and it exists because the MEDS entry was taken on bars
reporting no trades at all. But it was applied to the whole update rather
than to the untraded price: when an untraded pre-market quote became the
mark, the stop was switched off for that call entirely — including against
the regular-session CLOSE, which is a price 68 million shares actually
traded at.

TCRT is the live case. Called 3.37 on the 2026-10-14 pre-market screen, so
its 25% trail sat at 2.53. The regular session closed at 2.07 on 68.4M
shares — 18% through the stop — and the 02:42 ET run marked it 1.96 from an
untraded overnight quote and left it OPEN.

So the stop is now evaluated on the newest TRADED price, and the untraded
quote is applied afterwards for the mark alone.
"""

import pytest
from call_db import STATUS_OPEN, STATUS_STOPPED
from price_update import update_open_calls

from conftest import review_payload


def _cfg(config, *, stop_on_untraded=False):
    return {
        **config,
        "tracker": {
            **config["tracker"],
            "trailing_stop_pct": 25.0,
            "trailing_stop_atr_mult": None,
            "mark_extended_hours": True,
            "stop_on_untraded_extended": stop_on_untraded,
        },
    }


def _call(db, ticker="TCRT", entry=3.37, call_date="2026-10-14"):
    call_id = db.insert_call(
        review_payload(ticker, entry=entry),
        run_id="r1",
        allocation_usd=100.0,
        trail_floor_pct=25.0,
        trail_atr_mult=None,
    )
    # Dated like the live call, so the 10-14 bar is not read as pre-entry.
    db.conn.execute("UPDATE calls SET call_date = ? WHERE id = ?", (call_date, call_id))
    db.conn.commit()
    return call_id


def _points(*, close, close_as_of, ext, ext_as_of, ext_volume=0, volume=68_350_100):
    return {
        "TCRT": {
            "price": close,
            "as_of": close_as_of,
            "volume": volume,
            "extended_price": ext,
            "extended_as_of": ext_as_of,
            "extended_volume": ext_volume,
        }
    }


def test_the_traded_close_stops_the_call_even_under_an_untraded_quote(tmp_db, config):
    call_id = _call(tmp_db)
    result = update_open_calls(
        tmp_db,
        _cfg(config),
        prices=_points(close=2.07, close_as_of="2026-10-14", ext=1.96, ext_as_of="2026-10-14"),
        today="2026-10-15",
        regular_hours=False,
    )

    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    # Out at the traded close, not at the quote nobody paid.
    assert row["current_price"] == pytest.approx(2.07)
    assert row["pnl_pct"] == pytest.approx(-38.58, abs=0.01)
    update = next(item for item in result["updates"] if item["ticker"] == "TCRT")
    assert update["closed"] is True
    assert update["stopped"] is True


def test_an_untraded_quote_still_cannot_close_a_call_on_its_own(tmp_db, config):
    """The MEDS rule, unchanged: the traded close is ABOVE the stop here and
    only the untraded quote is through it."""
    call_id = _call(tmp_db)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices=_points(close=2.60, close_as_of="2026-10-14", ext=1.96, ext_as_of="2026-10-14"),
        today="2026-10-15",
        regular_hours=False,
    )

    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    # The mark still moves, so the number on screen is current.
    assert row["current_price"] == pytest.approx(1.96)


def test_the_untraded_quote_is_still_the_mark_when_the_close_holds(tmp_db, config):
    call_id = _call(tmp_db)
    result = update_open_calls(
        tmp_db,
        _cfg(config),
        prices=_points(close=3.40, close_as_of="2026-10-14", ext=3.60, ext_as_of="2026-10-15"),
        today="2026-10-15",
        regular_hours=False,
    )
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN
    assert tmp_db.call(call_id)["current_price"] == pytest.approx(3.60)
    update = next(item for item in result["updates"] if item["ticker"] == "TCRT")
    assert update["extended"] is True
    assert update["untraded"] is True


def test_a_traded_extended_print_closes_as_before(tmp_db, config):
    """Volume on the extended bar means somebody paid it; nothing changes."""
    call_id = _call(tmp_db)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices=_points(
            close=3.40, close_as_of="2026-10-14", ext=1.96, ext_as_of="2026-10-15", ext_volume=5000
        ),
        today="2026-10-15",
        regular_hours=False,
    )
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED
    assert tmp_db.call(call_id)["current_price"] == pytest.approx(1.96)


def test_a_stale_daily_close_is_not_replayed_into_a_stop(tmp_db, config):
    """The guard against the MEDS failure class: a close OLDER than the mark
    the book already holds is not evidence of anything new, and replaying it
    would stop a position on a session it already survived."""
    call_id = _call(tmp_db)
    # Monday: priced at 3.50 from a traded close.
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices=_points(close=3.50, close_as_of="2026-10-14", ext=None, ext_as_of=None),
        today="2026-10-14",
        regular_hours=False,
    )
    # Tuesday pre-market: the provider offers last WEEK's close, below the
    # stop, plus a fresh untraded quote above it.
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices=_points(close=2.00, close_as_of="2026-10-09", ext=3.45, ext_as_of="2026-10-15"),
        today="2026-10-15",
        regular_hours=False,
    )
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN
