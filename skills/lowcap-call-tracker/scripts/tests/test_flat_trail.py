"""The trailing stop is a flat 15% below the high-water mark.

A *flat* distance, not a scaled one: ``trailing_stop_atr_mult`` is off,
because with it on a 25% setting became 40.3% on VEEA and 49.0% on XRPN, and
the number in the config was then not the number in force on the positions
that mattered. The fixed stop (``tracker.sl_pct``) is a separate instrument
and is untouched.

The distance went 15 -> 25 on 2026-10-13 and back to 15 on 2026-10-17, both
operator decisions. What the 25% trail cost in between is on the record:
VEEA banked +35.8% where 15% would have banked about +62.5%, and NCPL peaked
at +49.4% and sat at +17.8% with its 25% stop still 4.9% away. What a 15%
trail cost BEFORE is also on the record — it closed positions on single
sessions of noise — so neither number is obviously right, and the operator's
is the one that governs.

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


def test_the_shipped_trail_is_a_flat_15_percent():
    tracker = _shipped()
    assert tracker["trailing_stop_pct"] == 15.0
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
        == 15.0
    )


def _flat(config):
    return {
        **config,
        "tracker": {**config["tracker"], "trailing_stop_pct": 15.0, "trailing_stop_atr_mult": None},
    }


def _open(db, *, entry=10.0, atr=3.0):
    review = review_payload("AAA", entry=entry)
    review["hit"] = {"ticker": "AAA", "atr": atr, "price": entry}
    return db.insert_call(
        review, run_id="r1", allocation_usd=100.0, trail_floor_pct=15.0, trail_atr_mult=None
    )


def test_a_double_that_gives_back_15_percent_closes(tmp_db, config):
    call_id = _open(tmp_db, entry=10.0)
    cfg = _flat(config)
    update_open_calls(tmp_db, cfg, prices={"AAA": 20.0})
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN
    update_open_calls(tmp_db, cfg, prices={"AAA": 17.0})

    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_STOPPED
    # Up 100%, closed +70%: the trail keeps more of the move than 25% did.
    assert row["pnl_pct"] == pytest.approx(70.0)
    assert "15%" in row["close_reason"]


def test_a_double_that_gives_back_14_percent_holds(tmp_db, config):
    call_id = _open(tmp_db, entry=10.0)
    cfg = _flat(config)
    update_open_calls(tmp_db, cfg, prices={"AAA": 20.0})
    update_open_calls(tmp_db, cfg, prices={"AAA": 17.2})
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


def test_a_call_that_never_gains_still_stops_at_15_percent(tmp_db, config):
    """The high-water mark starts at entry, so this is one rule, not two."""
    call_id = _open(tmp_db, entry=10.0)
    update_open_calls(tmp_db, _flat(config), prices={"AAA": 8.4})
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


def test_changing_the_setting_does_not_move_an_open_call(tmp_db, config):
    """ "In future" is the default, not a special case: the distance is stored
    on the row at entry. On 2026-10-17 this was the difference between a
    config edit and four immediate exits — AISP, FEAM, USDE and NCPL were all
    further off their highs than 15%."""
    call_id = _open(tmp_db, entry=10.0)  # opened on a 15% trail
    wider = {
        **config,
        "tracker": {**config["tracker"], "trailing_stop_pct": 40.0, "trailing_stop_atr_mult": None},
    }
    update_open_calls(tmp_db, wider, prices={"AAA": 8.4})
    # Still stopped at its own 15%, not spared by the new 40%.
    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED
    assert "15%" in tmp_db.call(call_id)["close_reason"]
