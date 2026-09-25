"""Voided calls: recorded as history, excluded from performance."""

import pytest
from call_db import STATUS_VOID
from stats import compute_stats

from conftest import review_payload


def _put(db, ticker="BEAR", entry=10.0, now_price=13.0):
    call_id = db.insert_call(
        review_payload(ticker, entry=entry, decision="SKIP", direction="short"), run_id="r1"
    )
    db.apply_price(call_id, now_price, close_threshold_pct=None)
    return call_id


def test_voiding_keeps_the_row_but_drops_it_from_performance(tmp_db, config):
    call_id = _put(tmp_db)
    tmp_db.insert_call(review_payload("AAA", entry=10.0, decision="TAKE"), run_id="r1")

    result = tmp_db.void_call(call_id, reason="not executable: no options, no borrow")
    row = tmp_db.call(call_id)
    assert result["voided"] is True
    assert row["status"] == STATUS_VOID
    assert row["pnl_pct"] == -30.0  # the history is intact
    assert "not executable" in row["close_reason"]

    stats = compute_stats(tmp_db, config)
    assert stats["overall"]["total"] == 1  # only the long counts
    assert stats["overall"]["voided_calls"] == 1
    assert stats["portfolio"]["calls_counted"] == 1


def test_a_voided_call_leaves_the_total_untouched(tmp_db, config):
    tmp_db.insert_call(review_payload("AAA", entry=10.0, decision="TAKE"), run_id="r1")
    tmp_db.apply_price(1, 11.0, close_threshold_pct=None)
    before = compute_stats(tmp_db, config)["portfolio"]["total_pnl_pct"]

    call_id = _put(tmp_db)
    tmp_db.void_call(call_id, reason="not executable")
    after = compute_stats(tmp_db, config)["portfolio"]["total_pnl_pct"]
    assert after == before == 10.0


def test_voiding_is_reported_so_it_cannot_hide(tmp_db, config):
    from stats import render_markdown, render_text

    tmp_db.insert_call(review_payload("AAA", entry=10.0, decision="TAKE"), run_id="r1")
    tmp_db.apply_price(1, 11.0, close_threshold_pct=None)
    tmp_db.void_call(_put(tmp_db), reason="not executable: no options, no borrow")
    stats = compute_stats(tmp_db, config)

    assert "1 voided" in render_text(stats)
    markdown = render_markdown(stats)
    assert "Voided" in markdown
    assert "not executable" in markdown


def test_a_voided_call_is_not_priced_again(tmp_db, config):
    from price_update import update_open_calls

    call_id = _put(tmp_db)
    tmp_db.void_call(call_id, reason="not executable")
    result = update_open_calls(tmp_db, config, prices={"BEAR": 20.0})
    assert result["updates"] == []
    assert tmp_db.call(call_id)["pnl_pct"] == -30.0


def test_voiding_frees_the_ticker_for_a_new_call(tmp_db):
    call_id = _put(tmp_db, ticker="SAME")
    tmp_db.void_call(call_id, reason="not executable")
    assert tmp_db.insert_call(review_payload("SAME", entry=5.0), run_id="r2") is not None


def test_voiding_an_unknown_call_raises(tmp_db):
    with pytest.raises(KeyError):
        tmp_db.void_call(999, reason="nope")
