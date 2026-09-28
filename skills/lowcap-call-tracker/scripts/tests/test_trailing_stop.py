"""The trailing stop: ride the move, leave when it turns."""

from call_db import STATUS_OPEN, STATUS_STOPPED
from price_update import update_open_calls
from stats import outcome

from conftest import review_payload


def _cfg(config, trail=15.0):
    return {**config, "tracker": {**config["tracker"], "trailing_stop_pct": trail}}


def _open(db, ticker="AAA", entry=10.0):
    return db.insert_call(review_payload(ticker, entry=entry), run_id="r1", allocation_usd=100.0)


def _walk(db, config, ticker, path):
    for price in path:
        update_open_calls(db, config, prices={ticker: price})


def test_the_peak_is_tracked_from_entry(tmp_db, config):
    call_id = _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [11.0, 13.0, 12.0])
    assert tmp_db.call(call_id)["peak_price"] == 13.0


def test_a_call_that_never_rises_stops_at_the_trail_below_entry(tmp_db, config):
    """With peak == entry, a 15% trail IS a 15% hard stop. One rule, not two."""
    call_id = _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [9.5, 8.4])
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert row["pnl_pct"] == -16.0
    assert "trailing stop" in row["close_reason"]


def test_a_winner_keeps_its_gain_when_it_turns(tmp_db, config):
    """Up 60%, then a 15% fade off the peak: the exit banks the rest."""
    call_id = _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [12.0, 16.0, 13.5])
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert row["peak_price"] == 16.0
    assert row["pnl_pct"] == 35.0  # exited at 13.5, still well above entry
    assert outcome(row) == "RIGHT"  # a stopped WINNER is right, not wrong


def test_a_shallow_pullback_does_not_trigger(tmp_db, config):
    call_id = _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [12.0, 16.0, 14.0])  # -12.5% off the peak
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


def test_the_trail_is_measured_from_the_peak_not_the_entry(tmp_db, config):
    call_id = _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [20.0, 17.5])  # +100%, then -12.5% off peak
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN
    _walk(tmp_db, _cfg(config), "AAA", [16.9])  # -15.5% off peak
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    assert row["pnl_pct"] == 69.0  # a big winner banked, not round-tripped


def test_a_stopped_loser_is_wrong(tmp_db, config):
    call_id = _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [10.5, 8.0])
    assert outcome(tmp_db.call(call_id)) == "WRONG"


def test_the_trail_can_be_switched_off(tmp_db, config):
    call_id = _open(tmp_db)
    _walk(
        tmp_db,
        {**config, "tracker": {**config["tracker"], "trailing_stop_pct": None}},
        "AAA",
        [16.0, 5.0],
    )
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


def test_a_stopped_call_frees_its_cash(tmp_db, config):
    from allocation import portfolio_state

    cfg = _cfg(config)
    cfg = {**cfg, "tracker": {**cfg["tracker"], "account_size": 1000.0}}
    _open(tmp_db)
    _walk(tmp_db, cfg, "AAA", [12.0, 16.0, 13.5])  # banks +35% on a $100 slice
    state = portfolio_state(tmp_db, cfg)
    assert state["allocated_usd"] == 0.0
    assert state["cash_usd"] == 1035.0
    assert state["realized_usd"] == 35.0


def test_a_stopped_call_is_reported_in_the_run(tmp_db, config):
    _open(tmp_db)
    update_open_calls(tmp_db, _cfg(config), prices={"AAA": 16.0})
    result = update_open_calls(tmp_db, _cfg(config), prices={"AAA": 13.0})
    update = result["updates"][0]
    assert update["closed"] is True
    assert update["stopped"] is True


def test_a_stopped_ticker_can_be_called_again(tmp_db, config):
    _open(tmp_db)
    _walk(tmp_db, _cfg(config), "AAA", [8.0])
    assert tmp_db.insert_call(review_payload("AAA", entry=8.0), run_id="r2") is not None
