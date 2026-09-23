"""An UNREVIEWED call must not display a contract nobody chose."""

from call_db import KIND_UNREVIEWED
from price_update import format_updates, update_open_calls
from run_cycle import unreviewed_review
from stats import compute_stats

from conftest import review_payload


def test_an_unreviewed_call_stores_no_instrument(tmp_db, stock_hit):
    call_id = tmp_db.insert_call(unreviewed_review(stock_hit, "backend down"), run_id="r1")
    row = tmp_db.call(call_id)
    assert row["kind"] == KIND_UNREVIEWED
    assert row["instrument"] is None
    assert row["strike"] is None
    assert row["expiry_date"] is None
    # PnL still needs a sign convention: the raw move of the underlying.
    assert row["direction"] == "long"


def test_an_unreviewed_call_prices_on_the_underlying_move(tmp_db, config, stock_hit):
    hit = {**stock_hit, "price": 10.0}
    tmp_db.insert_call(unreviewed_review(hit, "down"), run_id="r1")
    update_open_calls(tmp_db, config, prices={hit["ticker"]: 12.0})
    assert tmp_db.open_calls()[0]["pnl_pct"] == 20.0


def test_the_terminal_report_shows_a_dash_not_a_contract(tmp_db, config, stock_hit):
    tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
    result = update_open_calls(tmp_db, config, prices={stock_hit["ticker"]: 4.0})
    text = format_updates(result)
    assert "CALL" not in text
    assert "LONG" not in text
    assert "—" in text


def test_telegram_shows_a_dash_not_a_contract(tmp_db, config, stock_hit):
    import telegram_bot as tb

    tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
    row = tmp_db.open_calls()[0]
    contract = tb._contract(row)
    assert "CALL" not in contract.upper()
    assert "PUT" not in contract.upper()


def test_a_reviewed_call_still_shows_its_contract(tmp_db, config):
    tmp_db.insert_call(review_payload("AAA", decision="TAKE"), run_id="r1")
    result = update_open_calls(tmp_db, config, prices={"AAA": 11.0})
    assert "CALL" in format_updates(result)


def test_an_unreviewed_call_is_left_out_of_the_instrument_breakdown(tmp_db, config, stock_hit):
    """No instrument was chosen, so it belongs in no instrument bucket."""
    tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
    tmp_db.insert_call(review_payload("AAA", decision="TAKE"), run_id="r1")
    stats = compute_stats(tmp_db, config)
    assert set(stats["by_instrument"]) == {"call"}
    assert stats["by_instrument"]["call"]["total"] == 1
    assert stats["overall"]["total"] == 2


def test_a_late_review_attaches_the_contract(tmp_db, stock_hit):
    """The Risk Manager's choice arrives with the review, not before."""
    call_id = tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
    review = review_payload("SQZX", decision="TAKE", direction="short")
    review["verdicts"]["risk_manager"]["instrument"] = "put"
    updated = tmp_db.apply_review(call_id, review, run_id="r2")
    assert updated["instrument"] == "put"
    assert updated["direction"] == "short"


def test_reopening_the_database_does_not_reinvent_a_contract(tmp_path, stock_hit):
    """The legacy backfill must not overwrite a deliberate NULL."""
    from call_db import CallDatabase

    path = tmp_path / "reopen.db"
    with CallDatabase(path) as db:
        call_id = db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
        assert db.call(call_id)["instrument"] is None

    for _ in range(3):  # every open runs the migration
        with CallDatabase(path) as db:
            assert db.call(call_id)["instrument"] is None


def test_the_legacy_backfill_still_repairs_a_reviewed_row(tmp_path):
    """A pre-options reviewed row must still get its instrument."""
    from call_db import CallDatabase

    path = tmp_path / "legacy.db"
    with CallDatabase(path) as db:
        call_id = db.insert_call(review_payload("AAA", direction="short"), run_id="r1")
        db.conn.execute("UPDATE calls SET instrument = NULL WHERE id = ?", (call_id,))
        db.conn.commit()

    with CallDatabase(path) as db:
        assert db.call(call_id)["instrument"] == "put"
