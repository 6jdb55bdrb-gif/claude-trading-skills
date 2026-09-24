"""No puts: a bearish call on these names is not executable."""

import pytest
from role_review import _normalize_verdict, enforce_judge_gate, short_allowed

from conftest import review_payload


def _risk(direction="short", instrument="put"):
    return {"score": 7, "direction": direction, "instrument": instrument, "stop": 1.2}


def test_shorts_are_off_by_default(config):
    assert short_allowed(config) is False


def test_a_put_verdict_is_neutralized(config):
    verdict = _normalize_verdict("risk_manager", _risk(), config=config)
    assert verdict["instrument"] == "none"
    assert verdict["direction"] == "none"
    assert any("not executable" in reason for reason in verdict["reasons"])


def test_a_bare_short_direction_is_neutralized_too(config):
    verdict = _normalize_verdict("risk_manager", _risk(instrument=""), config=config)
    assert verdict["instrument"] == "none"
    assert verdict["direction"] == "none"


def test_a_long_call_is_untouched(config):
    verdict = _normalize_verdict(
        "risk_manager", _risk(direction="long", instrument="call"), config=config
    )
    assert verdict["instrument"] == "call"
    assert verdict["direction"] == "long"
    assert not any("not executable" in reason for reason in verdict["reasons"])


def test_a_neutralized_plan_forces_a_skip(config):
    """No executable plan is already a SKIP; the put just lands there."""
    verdicts = {"risk_manager": _normalize_verdict("risk_manager", _risk(), config=config)}
    judge = {
        "decision": "TAKE",
        "confidence": 80,
        "reason": "short the squeeze",
        "skeptic_answer": "x" * 40,
        "skeptic_objections_answered": True,
    }
    judged = enforce_judge_gate(judge, verdicts, config)
    assert judged["decision"] == "SKIP"
    assert "no executable plan" in judged["gate_overrides"][0]


def test_the_heuristic_risk_manager_never_shorts(config, stock_hit):
    """Even a climactic, extended setup gets 'none', not a put."""
    import heuristic_roles as heuristic

    blown_off = {
        **stock_hit,
        "sma20_pct": 85.0,
        "sma50_pct": 120.0,
        "rsi": 92.0,
        "change_pct": 60.0,
    }
    technician = heuristic.technician(blown_off)
    verdict = heuristic.risk_manager(
        blown_off,
        technician_verdict=technician,
        researcher_verdict={"score": 2},
        config=config,
    )
    assert verdict["instrument"] in {"call", "none"}
    assert verdict["direction"] in {"long", "none"}


def test_shorts_can_be_switched_back_on(config):
    config = {**config, "roles": {**config["roles"], "allow_short": True}}
    assert short_allowed(config) is True
    verdict = _normalize_verdict("risk_manager", _risk(), config=config)
    assert verdict["instrument"] == "put"
    assert verdict["direction"] == "short"


def test_a_put_can_never_be_stored_while_shorts_are_off(tmp_db, config):
    """Last line of defence: the database refuses what the policy forbids."""
    review = review_payload("BEAR", decision="TAKE", direction="short")
    review["verdicts"]["risk_manager"]["instrument"] = "put"
    with pytest.raises(ValueError, match="short"):
        tmp_db.insert_call(review, run_id="r1", allow_short=False)


def test_an_existing_put_still_prices_correctly(tmp_db, config):
    """History is not rewritten: a put already on the book keeps its maths."""
    call_id = tmp_db.insert_call(
        review_payload("OLD", entry=10.0, decision="SKIP", direction="short"), run_id="r1"
    )
    tmp_db.apply_price(call_id, 8.0, close_threshold_pct=None)
    assert tmp_db.call(call_id)["pnl_pct"] == 20.0


def test_closing_a_call_early_books_its_pnl_with_the_reason(tmp_db):
    call_id = tmp_db.insert_call(
        review_payload("OLD", entry=10.0, decision="SKIP", direction="short"), run_id="r1"
    )
    tmp_db.apply_price(call_id, 13.0, close_threshold_pct=None)  # the short went wrong
    result = tmp_db.close_call(call_id, reason="long-only policy: shorts are not executable")

    row = tmp_db.call(call_id)
    assert result["closed"] is True
    assert row["status"] != "OPEN"
    assert row["pnl_pct"] == -30.0  # the loss is booked, not erased
    assert "long-only" in row["close_reason"]


def test_closing_an_already_closed_call_is_harmless(tmp_db):
    call_id = tmp_db.insert_call(review_payload("OLD", entry=10.0), run_id="r1")
    tmp_db.apply_price(call_id, 11.0, close_threshold_pct=None)
    tmp_db.close_call(call_id, reason="first")
    tmp_db.close_call(call_id, reason="second")
    assert tmp_db.call(call_id)["close_reason"] == "first"
