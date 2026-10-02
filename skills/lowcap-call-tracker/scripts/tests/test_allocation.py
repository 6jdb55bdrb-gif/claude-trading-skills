"""Portfolio allocation: what the $1000 is doing, and what it is worth."""

from allocation import portfolio_state, shadow_state, slice_usd
from stats import compute_stats, render_text

from conftest import review_payload

ACCOUNT = 1000.0


def _config(config, **tracker):
    return {**config, "tracker": {**config["tracker"], "account_size": ACCOUNT, **tracker}}


def _open(db, ticker, entry, now_price, allocation):
    call_id = db.insert_call(
        review_payload(ticker, entry=entry), run_id="r1", allocation_usd=allocation
    )
    db.apply_price(call_id, now_price, close_threshold_pct=None)
    return call_id


# ------------------------------------------------------------------ sizing


def test_each_position_takes_a_fixed_slice(config):
    assert slice_usd(_config(config, position_pct=10.0), cash_available=1000.0) == 100.0
    assert slice_usd(_config(config, position_pct=25.0), cash_available=1000.0) == 250.0


def test_a_slice_never_exceeds_the_cash_left(config):
    """The last position is whatever is actually left, not a full slice."""
    assert slice_usd(_config(config, position_pct=10.0), cash_available=60.0) == 60.0


def test_no_cash_means_no_position(config):
    assert slice_usd(_config(config, position_pct=10.0), cash_available=0.0) is None
    assert slice_usd(_config(config, position_pct=10.0), cash_available=-5.0) is None


# --------------------------------------------------------------- portfolio


def test_an_untouched_account_is_all_cash(tmp_db, config):
    state = portfolio_state(tmp_db, _config(config))
    assert state["cash_usd"] == 1000.0
    assert state["allocated_usd"] == 0.0
    assert state["allocated_pct"] == 0.0
    assert state["portfolio_value_usd"] == 1000.0
    assert state["total_return_pct"] == 0.0


def test_allocation_and_value_track_the_stock(tmp_db, config):
    _open(tmp_db, "AAA", 10.0, 12.0, 100.0)  # +20% on $100 -> $120
    _open(tmp_db, "BBB", 10.0, 9.0, 100.0)  # -10% on $100 -> $90
    state = portfolio_state(tmp_db, _config(config))

    assert state["allocated_usd"] == 200.0
    assert state["allocated_pct"] == 20.0
    assert state["cash_usd"] == 800.0
    assert state["positions_value_usd"] == 210.0
    assert state["portfolio_value_usd"] == 1010.0
    assert state["total_return_pct"] == 1.0


def test_every_position_is_valued_individually(tmp_db, config):
    _open(tmp_db, "AAA", 10.0, 14.0, 250.0)
    state = portfolio_state(tmp_db, _config(config))
    position = state["positions"][0]
    assert position["ticker"] == "AAA"
    assert position["allocation_usd"] == 250.0
    assert position["value_usd"] == 350.0
    assert position["pnl_usd"] == 100.0


def test_a_closed_call_returns_its_value_to_cash(tmp_db, config):
    call_id = _open(tmp_db, "AAA", 10.0, 13.0, 100.0)
    tmp_db.close_call(call_id, reason="expired")
    state = portfolio_state(tmp_db, _config(config))

    assert state["allocated_usd"] == 0.0  # nothing is at risk any more
    assert state["cash_usd"] == 1030.0  # $100 went out, $130 came back
    assert state["portfolio_value_usd"] == 1030.0
    assert state["realized_usd"] == 30.0


def test_a_voided_call_never_touched_the_cash(tmp_db, config):
    call_id = _open(tmp_db, "BEAR", 10.0, 13.0, 100.0)
    tmp_db.void_call(call_id, reason="not executable")
    state = portfolio_state(tmp_db, _config(config))
    assert state["cash_usd"] == 1000.0
    assert state["portfolio_value_usd"] == 1000.0
    assert state["realized_usd"] == 0.0


def test_a_call_with_no_allocation_is_reported_not_valued(tmp_db, config):
    """A call opened before allocation existed must not fake a position."""
    call_id = tmp_db.insert_call(review_payload("OLD", entry=10.0), run_id="r1")
    tmp_db.apply_price(call_id, 20.0, close_threshold_pct=None)
    state = portfolio_state(tmp_db, _config(config))
    assert state["unallocated_calls"] == ["OLD"]
    assert state["portfolio_value_usd"] == 1000.0


def test_the_book_can_be_fully_allocated(tmp_db, config):
    for index in range(10):
        _open(tmp_db, f"T{index:02d}", 10.0, 10.0, 100.0)
    state = portfolio_state(tmp_db, _config(config))
    assert state["allocated_pct"] == 100.0
    assert state["cash_usd"] == 0.0
    assert slice_usd(_config(config), cash_available=state["cash_usd"]) is None


# ----------------------------------------------------------------- report


def test_the_terminal_block_states_the_allocation(tmp_db, config):
    _open(tmp_db, "AAA", 10.0, 12.0, 100.0)
    text = render_text(compute_stats(tmp_db, _config(config)))
    assert "ACCOUNT (TAKE only)" in text
    assert "$1,020.00" in text
    assert "10.0% allocated" in text
    assert "None" not in text


def test_telegram_states_the_allocation(tmp_db, config):
    import telegram_bot as tb

    _open(tmp_db, "AAA", 10.0, 12.0, 100.0)
    message = tb.format_stats_message(compute_stats(tmp_db, _config(config)))
    assert "$1,020.00" in message
    assert "10.0%" in message
    assert "None" not in message


def test_a_cycle_funds_each_new_call_from_the_cash_left(tmp_path, config):
    """Ten $100 slices fit in $1000; the eleventh call is recorded unfunded."""
    from call_db import CallDatabase
    from run_cycle import run_cycle

    from conftest import FIXTURE_HITS

    cfg = _config(
        config,
        position_pct=40.0,  # $400 a call: the third one cannot be funded in full
        stats_file=str(tmp_path / "s.md"),
        improvements_file=str(tmp_path / "i.md"),
        reports_dir=str(tmp_path / "r"),
    )
    run_cycle(
        cfg,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        telegram=False,
        db_path=str(tmp_path / "alloc.db"),
    )
    with CallDatabase(tmp_path / "alloc.db") as db:
        rows = db.all_calls()
        allocations = [row["allocation_usd"] for row in rows]
        state = portfolio_state(db, cfg)
        shadow = shadow_state(db, cfg)
    # The fixture gives two TAKEs and one SKIP. Every call carries a full
    # notional slice, but only the two TAKEs are money the account committed:
    # a SKIP is sized so the shadow book stays equal-weight, not funded.
    assert allocations == [400.0, 400.0, 400.0]
    assert state["allocated_usd"] == 800.0
    assert state["cash_usd"] == 200.0
    assert state["allocated_pct"] == 80.0
    # The shadow book carries all three at notional.
    assert shadow["allocated_usd"] == 1200.0


def test_a_take_is_still_capped_by_the_cash_the_account_has_left(tmp_path, config):
    """The account cannot commit money it does not have — the original point.

    Two TAKEs at 40% leave $200, so a third is funded with $200 and not $400.
    """
    from call_db import CallDatabase

    cfg = _config(config, position_pct=40.0)
    with CallDatabase(tmp_path / "cap.db") as db:
        for ticker in ("AAA", "BBB", "CCC"):
            cash = portfolio_state(db, cfg)["cash_usd"]
            db.insert_call(
                review_payload(ticker, decision="TAKE", entry=10.0),
                run_id="r1",
                allocation_usd=slice_usd(cfg, cash_available=cash),
            )
        allocations = [row["allocation_usd"] for row in db.all_calls()]
        state = portfolio_state(db, cfg)
    assert allocations == [400.0, 400.0, 200.0]
    assert state["allocated_usd"] == 1000.0
    assert state["cash_usd"] == 0.0
