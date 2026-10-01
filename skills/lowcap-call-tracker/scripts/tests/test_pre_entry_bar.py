"""A call is never marked with a bar from before it existed."""

from call_db import STATUS_OPEN
from price_update import update_open_calls

from conftest import review_payload


def _cfg(config, trail=15.0):
    return {**config, "tracker": {**config["tracker"], "trailing_stop_pct": trail}}


def test_a_bar_older_than_the_call_is_refused(tmp_db, config):
    """The reported failure: SDEV was called at 3.20 from the live screener on
    2026-10-01, then marked with the 2026-09-30 close of 2.59 — a session that
    ended before the call was made — and the trailing stop closed it at -19%."""
    call_id = tmp_db.insert_call(
        review_payload("SDEV", entry=3.20), run_id="r1", now="2026-10-01T10:18:56+00:00"
    )
    result = update_open_calls(
        tmp_db, _cfg(config), prices={"SDEV": {"price": 2.59, "as_of": "2026-09-30"}}
    )
    update = result["updates"][0]
    assert update["priced"] is False
    assert update["pre_entry"] is True
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["current_price"] == 3.20
    assert row["pnl_pct"] == 0.0


def test_a_bar_from_the_call_date_is_applied(tmp_db, config):
    call_id = tmp_db.insert_call(
        review_payload("SDEV", entry=3.20), run_id="r1", now="2026-10-01T10:18:56+00:00"
    )
    update_open_calls(tmp_db, _cfg(config), prices={"SDEV": {"price": 3.60, "as_of": "2026-10-01"}})
    assert tmp_db.call(call_id)["current_price"] == 3.60


def test_a_later_bar_is_applied(tmp_db, config):
    call_id = tmp_db.insert_call(
        review_payload("SDEV", entry=3.20), run_id="r1", now="2026-10-01T10:18:56+00:00"
    )
    update_open_calls(tmp_db, _cfg(config), prices={"SDEV": {"price": 2.80, "as_of": "2026-10-02"}})
    assert tmp_db.call(call_id)["current_price"] == 2.80


def test_a_dateless_price_is_still_applied(tmp_db, config):
    """--prices-json and fixtures carry no session and must keep working."""
    call_id = tmp_db.insert_call(
        review_payload("SDEV", entry=3.20), run_id="r1", now="2026-10-01T10:18:56+00:00"
    )
    update_open_calls(tmp_db, _cfg(config), prices={"SDEV": 2.59})
    assert tmp_db.call(call_id)["current_price"] == 2.59


def test_a_pre_entry_call_is_still_reported(tmp_db, config):
    """The position must not vanish from the report just because it is unpriced."""
    tmp_db.insert_call(
        review_payload("SDEV", entry=3.20), run_id="r1", now="2026-10-01T10:18:56+00:00"
    )
    result = update_open_calls(
        tmp_db, _cfg(config), prices={"SDEV": {"price": 2.59, "as_of": "2026-09-30"}}
    )
    assert len(result["updates"]) == 1
    assert "SDEV" in result["pre_entry_bars"]
    from price_update import format_updates

    assert "AWAITING FIRST BAR" in format_updates(result)
