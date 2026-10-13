"""The trailing stop is a flat 25% below the high-water mark.

The operator asked for one number: "if a position is up 100% and goes down
25% it should close the position". That is a *flat* distance, not a scaled
one, so ``trailing_stop_atr_mult`` is switched off — with it on, the same
25% floor became 40.3% on VEEA and 49.0% on XRPN, which is not the rule that
was asked for. The fixed stop (``tracker.sl_pct``) is untouched: "leave the
other stop loss as is".

These tests pin the shipped numbers, not just the mechanism, because the
mechanism was already right and the numbers were the whole request.
"""

import pytest
from call_db import STATUS_OPEN, STATUS_STOPPED, resolve_trail_pct
from price_update import update_open_calls

from config import load_config
from conftest import review_payload


def _shipped():
    return load_config()["tracker"]


def test_the_shipped_trail_is_a_flat_25_percent():
    tracker = _shipped()
    assert tracker["trailing_stop_pct"] == 25.0
    # None, not 1.0: a multiplier of 1 would still widen the trail on any
    # name whose ATR exceeds a quarter of its entry price.
    assert tracker["trailing_stop_atr_mult"] is None


def test_the_fixed_stop_is_left_alone():
    assert _shipped()["sl_pct"] == 30.0


@pytest.mark.parametrize("atr", [0.0, 0.5, 4.0, 9.9])
def test_the_distance_does_not_move_with_the_atr(atr):
    """A 99%-of-entry ATR used to buy a 148% trail. Now it buys nothing."""
    tracker = _shipped()
    assert (
        resolve_trail_pct(
            10.0,
            atr,
            floor_pct=tracker["trailing_stop_pct"],
            atr_mult=tracker["trailing_stop_atr_mult"],
        )
        == 25.0
    )


def _flat(config):
    return {
        **config,
        "tracker": {**config["tracker"], "trailing_stop_pct": 25.0, "trailing_stop_atr_mult": None},
    }


def _open(db, *, entry=10.0, atr=3.0):
    review = review_payload("AAA", entry=entry)
    review["hit"] = {"ticker": "AAA", "atr": atr, "price": entry}
    return db.insert_call(
        review, run_id="r1", allocation_usd=100.0, trail_floor_pct=25.0, trail_atr_mult=None
    )


def test_a_double_that_gives_back_25_percent_closes(tmp_db, config):
    """The operator's own example, run end to end."""
    call_id = _open(tmp_db, entry=10.0)
    cfg = _flat(config)
    update_open_calls(tmp_db, cfg, prices={"AAA": 20.0})
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN
    update_open_calls(tmp_db, cfg, prices={"AAA": 15.0})

    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    # Up 100%, closed +50%: the trail banks half the move, which is the point.
    assert row["pnl_pct"] == pytest.approx(50.0)
    assert "25%" in row["close_reason"]


def test_a_double_that_gives_back_24_percent_holds(tmp_db, config):
    call_id = _open(tmp_db, entry=10.0)
    cfg = _flat(config)
    update_open_calls(tmp_db, cfg, prices={"AAA": 20.0})
    update_open_calls(tmp_db, cfg, prices={"AAA": 15.2})
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


def test_a_call_that_never_gains_still_stops_at_25_percent(tmp_db, config):
    """The high-water mark starts at entry, so this is one rule, not two."""
    call_id = _open(tmp_db, entry=10.0)
    update_open_calls(tmp_db, _flat(config), prices={"AAA": 7.4})
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED
