"""The book marks on extended-hours prices, not only on completed daily bars.

Until now the mark came from the daily bar, so a pre-market run held the
previous close: at 05:38 ET on 6 October SDEV traded 10.39 while the book
showed Friday's 7.48 (+133.8% against a real +224.7%). The operator asked for
pre-market numbers to count, so `extended_price` is now folded in.

One guard comes with it, and it applies OUTSIDE regular hours only, so every
test here that exercises it states the session explicitly rather than inheriting
the wall clock. The mark drives the trailing stop, and a pre-market quote on a
thin microcap can print with ZERO volume — which is exactly how the
MEDS 5.16 entry was taken at the top of a 6am spike nobody traded. An
untraded extended print therefore moves the mark, the PnL and the peak, but it
cannot fire the stop. A traded one can.
"""

from call_db import STATUS_OPEN, STATUS_STOPPED
from price_update import fetch_price_points, format_updates, update_open_calls

from conftest import review_payload


def _cfg(config, *, extended=True, stop_on_untraded=False):
    return {
        **config,
        "tracker": {
            **config["tracker"],
            "trailing_stop_pct": 15.0,
            "trailing_stop_atr_mult": 1.5,
            "mark_extended_hours": extended,
            "stop_on_untraded_extended": stop_on_untraded,
        },
    }


def _open(db, ticker="AAA", entry=3.20, atr=0.43, called="2026-09-30T15:00:00+00:00"):
    review = review_payload(ticker, entry=entry)
    review["hit"] = {"ticker": ticker, "atr": atr, "price": entry}
    return db.insert_call(
        review,
        run_id="r1",
        now=called,
        allocation_usd=100.0,
        trail_floor_pct=15.0,
        trail_atr_mult=1.5,
    )


# --- the mark itself -------------------------------------------------------


def test_an_extended_price_becomes_the_mark(tmp_db, config):
    """The SDEV case: 10.39 pre-market must not read as Friday's 7.48."""
    call_id = _open(tmp_db)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 7.48,
                "as_of": "2026-10-02",
                "extended_price": 10.39,
                "extended_as_of": "2026-10-05",
                "extended_volume": 12000,
            }
        },
        today="2026-10-05",
    )
    row = tmp_db.call(call_id)
    assert row["current_price"] == 10.39
    assert round(row["pnl_pct"], 1) == 224.7


def test_the_extended_mark_is_flagged_in_the_report(tmp_db, config):
    _open(tmp_db)
    result = update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 7.48,
                "as_of": "2026-10-02",
                "extended_price": 10.39,
                "extended_as_of": "2026-10-05",
                "extended_volume": 12000,
            }
        },
        today="2026-10-05",
    )
    text = format_updates(result)
    assert "EXT" in text
    assert "PRIOR CLOSE" not in text  # the mark is current now


def test_turning_the_setting_off_keeps_the_daily_close(tmp_db, config):
    call_id = _open(tmp_db)
    update_open_calls(
        tmp_db,
        _cfg(config, extended=False),
        prices={
            "AAA": {
                "price": 7.48,
                "as_of": "2026-10-02",
                "extended_price": 10.39,
                "extended_as_of": "2026-10-05",
                "extended_volume": 12000,
            }
        },
        today="2026-10-05",
    )
    assert tmp_db.call(call_id)["current_price"] == 7.48


def test_a_stale_extended_print_is_ignored(tmp_db, config):
    """An extended bar older than the daily close is not an update."""
    call_id = _open(tmp_db)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 7.48,
                "as_of": "2026-10-02",
                "extended_price": 6.00,
                "extended_as_of": "2026-10-01",
                "extended_volume": 5000,
            }
        },
        today="2026-10-05",
    )
    assert tmp_db.call(call_id)["current_price"] == 7.48


def test_the_peak_ratchets_on_an_extended_mark(tmp_db, config):
    call_id = _open(tmp_db)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 7.48,
                "as_of": "2026-10-02",
                "extended_price": 10.39,
                "extended_as_of": "2026-10-05",
                "extended_volume": 12000,
            }
        },
        today="2026-10-05",
    )
    assert tmp_db.call(call_id)["peak_price"] == 10.39


# --- the untraded-quote guard ---------------------------------------------


def test_an_untraded_extended_print_cannot_fire_the_stop(tmp_db, config):
    """Zero volume is a quote, not a trade. It marks but must not close."""
    call_id = _open(tmp_db, entry=3.20, atr=0.43)  # trail 20.2%
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 4.00,
                "as_of": "2026-10-02",
                "extended_price": 2.00,
                "extended_as_of": "2026-10-05",
                "extended_volume": 0,
            }
        },
        today="2026-10-05",
        regular_hours=False,
    )
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["current_price"] == 2.00  # the mark still moved


def test_a_traded_extended_print_does_fire_the_stop(tmp_db, config):
    call_id = _open(tmp_db, entry=3.20, atr=0.43)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 4.00,
                "as_of": "2026-10-02",
                "extended_price": 2.00,
                "extended_as_of": "2026-10-05",
                "extended_volume": 45000,
            }
        },
        today="2026-10-05",
    )
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


def test_the_untraded_guard_can_be_switched_off(tmp_db, config):
    call_id = _open(tmp_db, entry=3.20, atr=0.43)
    update_open_calls(
        tmp_db,
        _cfg(config, stop_on_untraded=True),
        prices={
            "AAA": {
                "price": 4.00,
                "as_of": "2026-10-02",
                "extended_price": 2.00,
                "extended_as_of": "2026-10-05",
                "extended_volume": 0,
            }
        },
        today="2026-10-05",
    )
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


def test_a_regular_session_mark_always_stops_normally(tmp_db, config):
    """The guard is about EXTENDED prints only; regular bars are unaffected."""
    call_id = _open(tmp_db, entry=3.20, atr=0.43)
    update_open_calls(
        tmp_db,
        _cfg(config),
        prices={"AAA": {"price": 2.00, "as_of": "2026-10-05"}},
        today="2026-10-05",
    )
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


def test_an_untraded_mark_is_named_in_the_report(tmp_db, config):
    _open(tmp_db, entry=3.20, atr=0.43)
    result = update_open_calls(
        tmp_db,
        _cfg(config),
        prices={
            "AAA": {
                "price": 4.00,
                "as_of": "2026-10-02",
                "extended_price": 2.00,
                "extended_as_of": "2026-10-05",
                "extended_volume": 0,
            }
        },
        today="2026-10-05",
        regular_hours=False,
    )
    assert "EXT (untraded)" in format_updates(result)


# --- the fetcher -----------------------------------------------------------


def test_the_fetcher_carries_the_extended_fields(monkeypatch):
    import price_update

    monkeypatch.setattr(
        price_update, "_download_closes", lambda _t: {"SDEV": [("2026-10-02", 7.48, 7.60)]}
    )
    monkeypatch.setattr(
        price_update,
        "_download_extended",
        lambda _t: {
            "SDEV": {"price": 10.39, "as_of": "2026-10-05", "volume": 12000, "high": 10.50}
        },
    )
    point = fetch_price_points(["SDEV"])["SDEV"]
    assert point["price"] == 7.48
    assert point["extended_price"] == 10.39
    assert point["extended_as_of"] == "2026-10-05"
    assert point["extended_volume"] == 12000


def test_the_fetcher_survives_an_extended_failure(monkeypatch):
    """No extended data must degrade to the daily close, not raise."""
    import price_update

    monkeypatch.setattr(
        price_update, "_download_closes", lambda _t: {"SDEV": [("2026-10-02", 7.48, 7.60)]}
    )
    monkeypatch.setattr(price_update, "_download_extended", lambda _t: {})
    point = fetch_price_points(["SDEV"])["SDEV"]
    assert point["price"] == 7.48
    assert point["extended_price"] is None
