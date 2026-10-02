"""The high-water mark the trailing stop measures from.

`peak_price` is documented as the highest price seen since entry, but the
tracker only observes a price when a scan runs, so what it actually stores is
the highest price it *happened to sample*. On 2026-10-01 SDEV printed 4.54
intraday and the recorded peak was 4.24 — a 7% understatement, which silently
loosens every trailing stop measured from it.

`tracker.peak_from_session_high` makes the peak ratchet on the session's High
instead. It defaults to off, so the stop geometry never changes under an
operator who has not asked for it.
"""

from call_db import STATUS_OPEN, STATUS_STOPPED
from price_update import update_open_calls

from conftest import review_payload


def _cfg(config, *, session_high=False, floor=15.0, mult=1.5):
    return {
        **config,
        "tracker": {
            **config["tracker"],
            "trailing_stop_pct": floor,
            "trailing_stop_atr_mult": mult,
            "peak_from_session_high": session_high,
        },
    }


def _open(db, ticker="AAA", entry=3.20, atr=0.43):
    review = review_payload(ticker, entry=entry)
    review["hit"] = {"ticker": ticker, "atr": atr, "price": entry}
    return db.insert_call(
        review, run_id="r1", allocation_usd=100.0, trail_floor_pct=15.0, trail_atr_mult=1.5
    )


# --- the peak itself -------------------------------------------------------


def test_by_default_the_peak_still_only_tracks_sampled_prices(tmp_db, config):
    """Off by default: an operator's stops must not tighten unasked."""
    call_id = _open(tmp_db)
    update_open_calls(tmp_db, _cfg(config), prices={"AAA": {"price": 3.60, "high": 4.54}})
    assert tmp_db.call(call_id)["peak_price"] == 3.60


def test_with_the_flag_on_the_peak_takes_the_session_high(tmp_db, config):
    call_id = _open(tmp_db)
    update_open_calls(
        tmp_db, _cfg(config, session_high=True), prices={"AAA": {"price": 3.60, "high": 4.54}}
    )
    assert tmp_db.call(call_id)["peak_price"] == 4.54


def test_the_peak_never_falls_back_to_a_lower_session_high(tmp_db, config):
    """A quiet day after a big one must not reset the high-water mark."""
    call_id = _open(tmp_db)
    cfg = _cfg(config, session_high=True)
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 4.00, "high": 4.54}})
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 3.90, "high": 3.95}})
    assert tmp_db.call(call_id)["peak_price"] == 4.54


def test_a_missing_high_leaves_the_sampled_price_in_charge(tmp_db, config):
    """A provider that gives no High must not break pricing or reset the peak."""
    call_id = _open(tmp_db)
    cfg = _cfg(config, session_high=True)
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 4.00, "high": 4.54}})
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 3.95}})
    row = tmp_db.call(call_id)
    assert row["peak_price"] == 4.54
    assert row["current_price"] == 3.95


def test_a_bare_float_price_still_works_with_the_flag_on(tmp_db, config):
    call_id = _open(tmp_db)
    update_open_calls(tmp_db, _cfg(config, session_high=True), prices={"AAA": 3.60})
    assert tmp_db.call(call_id)["peak_price"] == 3.60


def test_a_high_below_the_entry_price_cannot_lower_the_peak(tmp_db, config):
    call_id = _open(tmp_db, entry=3.20)
    update_open_calls(
        tmp_db, _cfg(config, session_high=True), prices={"AAA": {"price": 2.90, "high": 3.00}}
    )
    assert tmp_db.call(call_id)["peak_price"] == 3.20  # the peak starts AT entry


# --- what it does to the stop ---------------------------------------------


def test_the_sdev_case_survives_on_the_sampled_peak(tmp_db, config):
    """What actually happened: peak 4.24, stop 3.39, the day's low 3.40."""
    call_id = _open(tmp_db, entry=3.20, atr=0.43)  # trail 20.2%
    cfg = _cfg(config)
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 4.24, "high": 4.54}})
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 3.40, "high": 4.54}})
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["peak_price"] == 4.24


def test_the_sdev_case_stops_out_on_the_true_session_high(tmp_db, config):
    """Peak 4.54 puts the 20.2% stop at 3.62, which the day's 3.40 low takes."""
    call_id = _open(tmp_db, entry=3.20, atr=0.43)
    cfg = _cfg(config, session_high=True)
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 4.24, "high": 4.54}})
    update_open_calls(tmp_db, cfg, prices={"AAA": {"price": 3.40, "high": 4.54}})
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert row["peak_price"] == 4.54
    assert "4.54" in row["close_reason"]


def test_the_flag_changes_nothing_for_a_call_that_never_rises(tmp_db, config):
    call_id = _open(tmp_db, entry=3.20, atr=0.43)
    update_open_calls(
        tmp_db, _cfg(config, session_high=True), prices={"AAA": {"price": 2.50, "high": 3.20}}
    )
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED  # -21.9%, past the 20.2% trail
    assert row["peak_price"] == 3.20
