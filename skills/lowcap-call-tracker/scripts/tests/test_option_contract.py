"""Contract selection and the expiry-based close rule."""

from datetime import date, datetime, timezone

import heuristic_roles as H
import pytest
from call_db import STATUS_EXPIRED, STATUS_OPEN, CallDatabase
from option_contract import (
    choose_expiry,
    choose_strike,
    classify_setup,
    days_to_expiry,
    is_expired,
    next_friday,
)
from price_update import update_open_calls
from run_cycle import run_cycle
from stats import outcome

from conftest import FIXTURE_HITS, review_payload

MONDAY = date(2026, 9, 21)


# ------------------------------------------------------------------ expiry


def test_expiries_land_on_a_friday(config):
    for setup in ("fade", "default", "catalyst"):
        expiry, _dte = choose_expiry(config=config, as_of=MONDAY, setup=setup)
        assert date.fromisoformat(expiry).weekday() == 4, setup


def test_horizon_follows_the_setup(config):
    fade, fade_dte = choose_expiry(config=config, as_of=MONDAY, setup="fade")
    default, default_dte = choose_expiry(config=config, as_of=MONDAY, setup="default")
    catalyst, catalyst_dte = choose_expiry(config=config, as_of=MONDAY, setup="catalyst")
    assert fade_dte < default_dte < catalyst_dte
    assert fade < default < catalyst


def test_horizons_are_configurable(config):
    config["tracker"]["options"]["catalyst_dte"] = 90
    _expiry, dte = choose_expiry(config=config, as_of=MONDAY, setup="catalyst")
    assert dte >= 90


def test_next_friday_is_idempotent_on_a_friday():
    friday = date(2026, 9, 25)
    assert next_friday(friday) == friday
    assert next_friday(date(2026, 9, 26)).weekday() == 4  # Saturday rolls forward


@pytest.mark.parametrize(
    ("price", "call_strike", "put_strike"),
    [
        (1.04, 1.5, 1.0),  # $0.50 increments under $10
        (7.30, 7.5, 7.0),
        (12.30, 13.0, 12.0),  # $1 increments under $25
        (48.00, 50.0, 45.0),  # $5 increments above
    ],
)
def test_strike_reaches_the_way_the_trade_needs(price, call_strike, put_strike):
    assert choose_strike(price, "call") == call_strike
    assert choose_strike(price, "put") == put_strike


def test_strike_is_none_without_a_price():
    assert choose_strike(None, "call") is None
    assert choose_strike(0, "put") is None


# ------------------------------------------------------------------ setups


def test_a_climactic_move_is_a_fade():
    assert (
        classify_setup(
            technician={"volume_pattern": "climactic", "extension_pct_sma20": 83},
            researcher={"score": 3},
            skeptic={"score": 10},
        )
        == "fade"
    )


def test_a_dated_catalyst_earns_the_long_horizon():
    assert (
        classify_setup(
            technician={"volume_pattern": "confirming", "extension_pct_sma20": 12},
            researcher={"catalyst_type": "fda_regulatory", "score": 8},
            skeptic={"score": 2},
        )
        == "catalyst"
    )


def test_no_catalyst_and_no_climax_is_the_default_horizon():
    assert (
        classify_setup(
            technician={"volume_pattern": "confirming", "extension_pct_sma20": 20},
            researcher={"catalyst_type": "none_found", "score": 3},
            skeptic={"score": 4},
        )
        == "default"
    )


# ------------------------------------------------------------ risk manager


def test_an_upside_setup_becomes_a_call(stock_hit, config):
    verdict = H.risk_manager(
        stock_hit,
        technician_verdict=H.technician(stock_hit),
        skeptic_verdict={"score": 3},
        researcher_verdict={"catalyst_type": "fda_regulatory", "score": 8},
        config=config,
        as_of=MONDAY,
    )
    assert verdict["instrument"] == "call"
    assert verdict["direction"] == "long"  # PnL convention for a call
    assert verdict["strike"] >= stock_hit["price"]
    assert verdict["expiry_setup"] == "catalyst"
    assert date.fromisoformat(verdict["expiry_date"]) > MONDAY


def test_a_fade_becomes_a_put_on_a_shorter_contract(stock_hit, config):
    hit = {**stock_hit, "sma20_pct": 83.0, "rel_volume": 12.0}
    verdict = H.risk_manager(
        hit,
        technician_verdict=H.technician(hit),
        skeptic_verdict={"score": 10},
        researcher_verdict={"catalyst_type": "none_found", "score": 2},
        config=config,
        as_of=MONDAY,
    )
    assert verdict["instrument"] == "put"
    assert verdict["direction"] == "short"
    assert verdict["strike"] <= hit["price"]
    assert verdict["expiry_setup"] == "fade"


def test_no_plan_means_no_contract(config):
    verdict = H.risk_manager({"ticker": "X", "asset_type": "stock"}, config=config)
    assert verdict["instrument"] == "none"
    assert verdict["expiry_date"] is None


def test_the_contract_reaches_the_call_record(tmp_db, config, stock_hit):
    review = review_payload("AAA", entry=3.8)
    review["verdicts"]["risk_manager"].update(
        {"instrument": "put", "strike": 3.5, "expiry_date": "2026-10-16", "direction": "short"}
    )
    call_id = tmp_db.insert_call(review, run_id="r1")
    row = tmp_db.call(call_id)
    assert row["instrument"] == "put"
    assert row["strike"] == 3.5
    assert row["expiry_date"] == "2026-10-16"
    assert row["direction"] == "short"  # put keeps short PnL maths


# ------------------------------------------------------------- expiry close


def test_days_to_expiry_and_is_expired():
    assert days_to_expiry("2026-09-25", MONDAY) == 4
    assert days_to_expiry(None) is None
    assert is_expired("2026-09-18", MONDAY) is True
    assert is_expired("2026-09-25", MONDAY) is False


def test_a_call_survives_a_crash_until_its_contract_expires(tmp_db, config):
    """The whole point of the change: no drawdown closes a call any more."""
    call_id = tmp_db.insert_call(review_payload("DEEP", entry=10.0), run_id="r1")
    tmp_db.conn.execute("UPDATE calls SET expiry_date = ? WHERE id = ?", ("2099-01-16", call_id))
    tmp_db.conn.commit()
    update_open_calls(tmp_db, config, prices={"DEEP": 0.5})  # -95%
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_OPEN
    assert row["pnl_pct"] == pytest.approx(-95.0)
    assert outcome(row) == "NEUTRAL"


def test_the_price_update_settles_an_expired_contract(tmp_db, config):
    call_id = tmp_db.insert_call(review_payload("GONE", entry=10.0), run_id="r1")
    tmp_db.conn.execute("UPDATE calls SET expiry_date = '2026-01-16' WHERE id = ?", (call_id,))
    tmp_db.conn.commit()
    result = update_open_calls(tmp_db, config, prices={"GONE": 8.0})
    update = result["updates"][0]
    assert update["expired"] is True
    assert result["closed"] == 1
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_EXPIRED
    assert row["pnl_pct"] == pytest.approx(-20.0)  # settled at its last price
    assert outcome(row) == "WRONG"


def test_an_expired_winner_settles_as_right(tmp_db, config):
    call_id = tmp_db.insert_call(review_payload("PAID", entry=10.0), run_id="r1")
    tmp_db.conn.execute("UPDATE calls SET expiry_date = '2026-01-16' WHERE id = ?", (call_id,))
    tmp_db.conn.commit()
    update_open_calls(tmp_db, config, prices={"PAID": 14.0})
    assert outcome(tmp_db.call(call_id)) == "RIGHT"


def test_expiry_closing_can_be_switched_off(tmp_db, config):
    config["tracker"]["close_on_expiry"] = False
    config["tracker"]["close_threshold_pct"] = -80.0
    call_id = tmp_db.insert_call(review_payload("KEEP", entry=10.0), run_id="r1")
    tmp_db.conn.execute("UPDATE calls SET expiry_date = '2026-01-16' WHERE id = ?", (call_id,))
    tmp_db.conn.commit()
    update_open_calls(tmp_db, config, prices={"KEEP": 9.0})
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


def test_an_expired_ticker_can_be_called_again(tmp_db, config):
    first = tmp_db.insert_call(review_payload("AGAIN", entry=10.0), run_id="r1")
    tmp_db.conn.execute("UPDATE calls SET expiry_date = '2026-01-16' WHERE id = ?", (first,))
    tmp_db.conn.commit()
    update_open_calls(tmp_db, config, prices={"AGAIN": 9.0})
    assert tmp_db.insert_call(review_payload("AGAIN", entry=9.0), run_id="r2") is not None


# ------------------------------------------------------------- cycle + report


def test_a_full_cycle_records_contracts(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        telegram=False,
        db_path=str(tmp_path / "cycle.db"),
        now=datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc),
    )
    assert len(report["new_calls"]) == 3
    with CallDatabase(tmp_path / "cycle.db") as db:
        rows = {row["ticker"]: row for row in db.all_calls()}
        assert {row["instrument"] for row in rows.values()} <= {"call", "put"}
        assert all(row["expiry_date"] for row in rows.values())
        # The climactic PMPX fade gets a shorter contract than the FDA catalyst.
        assert rows["PMPX"]["instrument"] == "put"
        assert rows["PMPX"]["expiry_date"] < rows["SQZX"]["expiry_date"]


def test_reports_name_the_contract(config, tmp_db):
    import telegram_bot as tb

    review = review_payload("AAA", entry=3.8)
    review["verdicts"]["risk_manager"].update(
        {"instrument": "call", "strike": 4.0, "expiry_date": "2099-11-06"}
    )
    tmp_db.insert_call(review, run_id="r1")
    report = tb.format_report_message(tmp_db, config)
    assert "CALL 4.00" in report
    assert "exp 2099-11-06" in report
    detail = tb.format_call_detail(tmp_db, "AAA")
    assert "contract:" in detail and "CALL" in detail
