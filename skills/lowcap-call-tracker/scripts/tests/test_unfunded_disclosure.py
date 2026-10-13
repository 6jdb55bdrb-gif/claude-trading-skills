"""An open call with no money behind it has to say so on its own line.

The capital gate stops NEW unfunded calls being recorded, but six of them
were already open when it went in, and they read in the price-update block
exactly like the eleven positions the account actually held. That is the
confusion the operator objected to, and the gate alone does not fix it for
rows that already exist.
"""

from price_update import format_updates, update_open_calls
from telegram_bot import format_run_notification

from conftest import review_payload


def _two(db):
    funded = db.insert_call(review_payload("PAID", entry=10.0), run_id="r1", allocation_usd=100.0)
    tracked = db.insert_call(review_payload("FREE", entry=10.0), run_id="r1", allocation_usd=None)
    return funded, tracked


def test_the_report_marks_the_unfunded_call(tmp_db, config):
    _two(tmp_db)
    result = update_open_calls(tmp_db, config, prices={"PAID": 11.0, "FREE": 11.0})
    text = format_updates(result)

    paid, free = (line for line in text.splitlines() if "PAID" in line or "FREE" in line)
    assert "UNFUNDED" in free
    assert "UNFUNDED" not in paid


def test_the_update_carries_the_size(tmp_db, config):
    _two(tmp_db)
    result = update_open_calls(tmp_db, config, prices={"PAID": 11.0, "FREE": 11.0})
    sizes = {update["ticker"]: update["allocation_usd"] for update in result["updates"]}
    assert sizes == {"PAID": 100.0, "FREE": None}


def test_the_push_marks_the_unfunded_call(tmp_db, config):
    _two(tmp_db)
    report = {
        "session": {"as_of": "2026-10-13", "reason": "test"},
        "screening_ran": True,
        "new_calls": [],
        "price_update": update_open_calls(tmp_db, config, prices={"PAID": 11.0, "FREE": 11.0}),
    }
    message = format_run_notification(report, config)

    free = next(line for line in message.splitlines() if "FREE" in line)
    paid = next(line for line in message.splitlines() if "PAID" in line)
    assert "unfunded" in free
    assert "unfunded" not in paid
