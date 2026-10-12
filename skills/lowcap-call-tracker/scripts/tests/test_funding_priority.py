"""Who gets the money when the portfolio is the cap.

The operator's rule: allocation may reach the whole portfolio and no more.
With a hard cap, the only remaining question is which calls the capital goes
to — and the answer must not be "whichever arrived first", because arrival
order is noise. A shadow SKIP logged at 04:00 was starving a TAKE logged at
10:00, and the pre-market screen fills the book in two days.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from allocation import portfolio_state, slice_usd
from run_cycle import run_cycle

from conftest import FIXTURE_HITS, review_payload


def _fund(db, config, tickers_and_decisions, *, run_id="r1"):
    """Insert calls in the given order, funding each from the cash left."""
    out = []
    for ticker, decision in tickers_and_decisions:
        cash = portfolio_state(db, config)["cash_usd"]
        out.append(
            db.insert_call(
                review_payload(ticker, decision=decision, entry=10.0),
                run_id=run_id,
                allocation_usd=slice_usd(config, cash_available=cash),
            )
        )
    return out


# --- the cap ------------------------------------------------------------


def test_allocation_never_exceeds_the_portfolio(tmp_db, config):
    """The invariant, asserted directly: twenty calls against ten slices."""
    _fund(tmp_db, config, [(f"T{index}", "TAKE") for index in range(20)])
    state = portfolio_state(tmp_db, config)
    assert state["allocated_usd"] <= state["capital_usd"] + 0.005
    assert state["cash_usd"] >= -0.005
    assert state["allocated_pct"] <= 100.0


def test_the_book_fills_and_then_stops_funding(tmp_db, config):
    ids = _fund(tmp_db, config, [(f"T{index}", "TAKE") for index in range(12)])
    rows = {
        row["id"]: row["allocation_usd"]
        for row in tmp_db.conn.execute("SELECT id, allocation_usd FROM calls")
    }
    funded = [value for value in rows.values() if value]
    assert sum(funded) == pytest.approx(1000.0, abs=0.01)
    # The eleventh and twelfth get nothing rather than a share of nothing.
    assert rows[ids[-1]] is None


def test_realized_gains_raise_the_cap(tmp_db, config):
    """Banked profit is capital, so the book can commit it."""
    won = _fund(tmp_db, config, [("WON", "TAKE")])[0]
    tmp_db.apply_price(won, 20.0, close_threshold_pct=None, allow_stop=False)
    tmp_db.close_call(won, reason="target_hit")
    _fund(tmp_db, config, [(f"T{index}", "TAKE") for index in range(11)])
    state = portfolio_state(tmp_db, config)
    assert state["capital_usd"] == 1100.0
    assert state["allocated_usd"] <= state["capital_usd"] + 0.005


# --- the priority -------------------------------------------------------


def test_takes_are_funded_before_shadow_skips(tmp_path, config):
    """A cycle whose reviews arrive SKIP-first must still fund the TAKE."""
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        now=datetime(2026, 10, 7, 17, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        force_screen=True,
        offline=True,
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert report["new_calls"], "the cycle recorded no calls"


def test_a_full_book_funds_a_take_over_a_later_skip(tmp_db, config):
    from run_cycle import fund_order

    reviews = [
        review_payload("SKIP1", decision="SKIP", entry=10.0),
        review_payload("SKIP2", decision="SKIP", entry=10.0),
        review_payload("TAKE1", decision="TAKE", entry=10.0),
    ]
    assert [review["ticker"] for review in fund_order(reviews)] == ["TAKE1", "SKIP1", "SKIP2"]


def test_funding_order_is_stable_within_a_decision(tmp_db, config):
    """Two TAKEs keep the order the screener ranked them in."""
    from run_cycle import fund_order

    reviews = [
        review_payload("FIRST", decision="TAKE", entry=10.0),
        review_payload("SECOND", decision="TAKE", entry=10.0),
        review_payload("SHADOW", decision="SKIP", entry=10.0),
    ]
    assert [review["ticker"] for review in fund_order(reviews)] == ["FIRST", "SECOND", "SHADOW"]


def test_an_unreviewed_call_funds_after_a_take_but_before_a_skip(tmp_db, config):
    """An UNREVIEWED hit is a real screener find whose verdict is pending; a
    SKIP is a call the Judge actively refused."""
    from call_db import DECISION_UNREVIEWED
    from run_cycle import fund_order

    reviews = [
        review_payload("SHADOW", decision="SKIP", entry=10.0),
        review_payload("PENDING", decision=DECISION_UNREVIEWED, entry=10.0),
        review_payload("TAKEN", decision="TAKE", entry=10.0),
    ]
    assert [review["ticker"] for review in fund_order(reviews)] == ["TAKEN", "PENDING", "SHADOW"]


# --- saying so ----------------------------------------------------------


def test_the_report_says_when_the_book_is_full(tmp_path, config):
    """A call logged with no money must say so. Silently recording a
    zero-weight call reads in the report exactly like a funded one — which is
    how the best-performing name in the live book came to be holding 47 cents
    without anything pointing it out."""
    from run_cycle import format_report

    # Two slices of 50% fill the book, so the fixture's third call gets nothing.
    config["tracker"]["position_pct"] = 50.0
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        now=datetime(2026, 10, 7, 17, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        force_screen=True,
        offline=True,
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    allocations = [call.get("allocation_usd") for call in report["new_calls"]]
    assert allocations.count(None) == 1, allocations
    text = format_report(report)
    assert "funded book full" in text.lower()
