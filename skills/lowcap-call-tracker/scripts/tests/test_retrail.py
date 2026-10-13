"""Re-setting the trail on positions that are already open.

Each call stores its own trail distance, resolved at entry, precisely so that
editing the config never re-stops a live position. That is the right default
and it is also why changing ``trailing_stop_pct`` to 25 left the open book on
the distances it was taken with — 15% on most, 40.3% on VEEA, 49.0% on XRPN.
An operator who changes the rule and means it needs one deliberate step that
moves the open positions onto it.

The step is deliberate in both directions:

* it reports what each call moves from and to **before** writing anything;
* it names every call the new distance would close immediately, because
  tightening a trail onto a position that has already given back more than
  the new distance is an exit, not a setting.
"""

import pytest
from call_db import STATUS_OPEN, STATUS_STOPPED
from retrail import apply_retrail, format_plan, plan_retrail

from conftest import review_payload


def _flat(config, pct=25.0):
    return {
        **config,
        "tracker": {**config["tracker"], "trailing_stop_pct": pct, "trailing_stop_atr_mult": None},
    }


def _call(db, ticker, *, entry, peak, now, trail, atr=None):
    review = review_payload(ticker, entry=entry)
    if atr is not None:
        review["hit"] = {"ticker": ticker, "atr": atr, "price": entry}
    call_id = db.insert_call(
        review, run_id="r1", allocation_usd=100.0, trail_floor_pct=trail, trail_atr_mult=None
    )
    db.conn.execute(
        "UPDATE calls SET peak_price = ?, current_price = ? WHERE id = ?", (peak, now, call_id)
    )
    db.conn.commit()
    return call_id


def test_the_plan_names_the_old_and_new_distance(tmp_db, config):
    _call(tmp_db, "AAA", entry=10.0, peak=11.0, now=10.5, trail=15.0)
    (entry,) = plan_retrail(tmp_db, _flat(config))

    assert entry["ticker"] == "AAA"
    assert entry["from_pct"] == 15.0
    assert entry["to_pct"] == 25.0
    assert entry["direction"] == "wider"
    assert entry["would_stop"] is False
    # The level, not just the percentage: a stop is a price.
    assert entry["new_stop"] == pytest.approx(8.25)


def test_a_call_already_past_the_new_trail_is_flagged_not_hidden(tmp_db, config):
    # Peaked at 4.30, now 3.07: 28.6% off the high, past a 25% trail.
    _call(tmp_db, "MEDS", entry=4.30, peak=4.30, now=3.07, trail=37.7)
    (entry,) = plan_retrail(tmp_db, _flat(config))

    assert entry["direction"] == "tighter"
    assert entry["would_stop"] is True
    assert entry["drop_pct"] == pytest.approx(-28.6, abs=0.05)
    assert "would close" in format_plan([entry])


def test_nothing_is_written_by_planning(tmp_db, config):
    call_id = _call(tmp_db, "AAA", entry=10.0, peak=11.0, now=10.5, trail=15.0)
    plan_retrail(tmp_db, _flat(config))
    assert tmp_db.call(call_id)["trail_pct"] == 15.0


def test_applying_writes_the_new_distance(tmp_db, config):
    call_id = _call(tmp_db, "AAA", entry=10.0, peak=11.0, now=10.5, trail=15.0)
    result = apply_retrail(tmp_db, _flat(config))

    assert tmp_db.call(call_id)["trail_pct"] == 25.0
    assert result["changed"] == 1
    assert result["would_stop"] == []


def test_applying_does_not_itself_close_a_position(tmp_db, config):
    """The stop belongs to the price update, which is the only thing that
    compares a trail to a traded price. Writing the distance must not double
    as an exit, or the close would carry no price and no timestamp."""
    call_id = _call(tmp_db, "MEDS", entry=4.30, peak=4.30, now=3.07, trail=37.7)
    apply_retrail(tmp_db, _flat(config))

    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["trail_pct"] == 25.0


def test_the_next_price_update_then_closes_it(tmp_db, config):
    from price_update import update_open_calls

    call_id = _call(tmp_db, "MEDS", entry=4.30, peak=4.30, now=3.07, trail=37.7)
    apply_retrail(tmp_db, _flat(config))
    update_open_calls(tmp_db, _flat(config), prices={"MEDS": 3.07})

    assert tmp_db.call(call_id)["status"] == STATUS_STOPPED


def test_only_widen_leaves_a_tightening_call_alone(tmp_db, config):
    """The escape hatch for an operator who wants the new rule on new calls
    and on anything it loosens, without an exit they did not ask for."""
    loosen = _call(tmp_db, "AAA", entry=10.0, peak=11.0, now=10.5, trail=15.0)
    tighten = _call(tmp_db, "MEDS", entry=4.30, peak=4.30, now=3.07, trail=37.7)
    result = apply_retrail(tmp_db, _flat(config), only_widen=True)

    assert tmp_db.call(loosen)["trail_pct"] == 25.0
    assert tmp_db.call(tighten)["trail_pct"] == 37.7
    assert result["skipped"] == ["MEDS"]


def test_a_closed_call_is_never_touched(tmp_db, config):
    call_id = _call(tmp_db, "AAA", entry=10.0, peak=11.0, now=10.5, trail=15.0)
    tmp_db.close_call(call_id, reason="test")
    assert plan_retrail(tmp_db, _flat(config)) == []


def test_a_disabled_trail_is_refused_rather_than_guessed(tmp_db, config):
    """``trailing_stop_pct: null`` means no trailing stop. Re-setting every
    open call to "no stop" is a plausible reading and a terrible one, so it
    is refused instead."""
    _call(tmp_db, "AAA", entry=10.0, peak=11.0, now=10.5, trail=15.0)
    off = {**config, "tracker": {**config["tracker"], "trailing_stop_pct": None}}
    with pytest.raises(ValueError, match="no trailing stop"):
        plan_retrail(tmp_db, off)
