"""Rotation and the capital gate inside a real cycle, and in the messages.

The policy is tested in test_rotation.py. This is about the wiring: a cycle
with no cash must close a loser, fund the TAKE, and SAY SO in both the
terminal report and the Telegram push. A rotation that happens silently is
worse than no rotation at all — the operator would find a position gone with
nothing naming what took its money.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from allocation import portfolio_state
from call_db import STATUS_OPEN, CallDatabase
from run_cycle import format_report, run_cycle
from telegram_bot import format_run_notification

from conftest import FIXTURE_HITS, review_payload

ZURICH = ZoneInfo("Europe/Zurich")


def _seed(path, *, ticker="DEAD", confidence=20, mark=5.0, allocation=1000.0):
    """One position holding the entire account, down 50%, low conviction."""
    with CallDatabase(path) as db:
        call_id = db.insert_call(
            review_payload(ticker, confidence=confidence, entry=10.0),
            run_id="seed",
            allocation_usd=allocation,
        )
        db.apply_price(call_id, mark, close_threshold_pct=None, allow_stop=False)
        return call_id


def _cycle(config, path, **kwargs):
    return run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        now=datetime(2026, 10, 7, 17, 0, tzinfo=ZURICH),
        force_screen=True,
        offline=True,
        db_path=str(path),
        telegram=False,
        prices={},
        **kwargs,
    )


def test_a_cycle_with_no_cash_rotates_and_funds_the_take(tmp_path, config):
    path = tmp_path / "calls.db"
    dead = _seed(path)
    report = _cycle(config, path)

    assert [entry["ticker"] for entry in report["rotations"]] == ["DEAD"]
    assert report["rotations"][0]["for_ticker"] == "SQZX"
    # $1,000 in at 10.00, marked 5.00: $500 of cash, and a $100 slice of it.
    assert report["rotations"][0]["freed_usd"] == pytest.approx(500.0, abs=0.01)
    assert report["new_calls"][0]["allocation_usd"] == pytest.approx(100.0, abs=0.01)

    with CallDatabase(path) as db:
        assert db.call(dead)["status"] != STATUS_OPEN
        assert "SQZX" in db.call(dead)["close_reason"]
        # The money moved; it was not duplicated.
        state = portfolio_state(db, config)
        assert state["allocated_usd"] == pytest.approx(100.0, abs=0.01)


def test_the_report_names_both_sides_of_the_rotation(tmp_path, config):
    path = tmp_path / "calls.db"
    _seed(path)
    text = format_report(_cycle(config, path))

    assert "ROTATED OUT FOR CASH" in text
    assert "DEAD" in text
    assert "into SQZX" in text


def test_the_push_names_both_sides_of_the_rotation(tmp_path, config):
    path = tmp_path / "calls.db"
    _seed(path)
    message = format_run_notification(_cycle(config, path), config)

    assert "Rotated for cash" in message
    assert "DEAD" in message
    assert "SQZX" in message


def test_a_winner_is_left_alone_and_the_call_is_not_made(tmp_path, config):
    """The whole account in a position that is UP. Nothing is displaceable, so
    the TAKE is a capital skip — not an unfunded row."""
    path = tmp_path / "calls.db"
    won = _seed(path, mark=18.0)
    report = _cycle(config, path)

    assert report["rotations"] == []
    assert report["new_calls"] == []
    assert [skip["ticker"] for skip in report["capital_skips"]] == ["SQZX"]
    assert report["capital_skips"][0]["wanted_usd"] == pytest.approx(100.0, abs=0.01)

    with CallDatabase(path) as db:
        assert db.call(won)["status"] == STATUS_OPEN
        assert db.open_call_for("SQZX") is None, "a gated call must leave no row"


def test_the_report_says_a_call_was_not_made(tmp_path, config):
    path = tmp_path / "calls.db"
    _seed(path, mark=18.0)
    text = format_report(_cycle(config, path))

    assert "capital skip: SQZX" in text
    assert "not called" in text


def test_the_push_says_a_call_was_not_made(tmp_path, config):
    path = tmp_path / "calls.db"
    _seed(path, mark=18.0)
    message = format_run_notification(_cycle(config, path), config)

    assert "SQZX" in message
    assert "no cash" in message


def test_the_gate_can_be_switched_off_for_the_old_behaviour(tmp_path, config):
    path = tmp_path / "calls.db"
    _seed(path, mark=18.0)
    config["tracker"]["capital_gated"] = False
    report = _cycle(config, path)

    assert report["capital_skips"] == []
    assert report["new_calls"][0]["allocation_usd"] is None
    assert "funded book full" in format_report(report).lower()


def test_a_low_conviction_take_does_not_displace(tmp_path, config):
    """The seeded loser carries confidence 100 and so does the fixture TAKE.
    Equal is not higher, so nothing is displaced and the call is not made."""
    path = tmp_path / "calls.db"
    kept = _seed(path, confidence=100)
    report = _cycle(config, path)

    assert report["rotations"] == []
    assert [skip["ticker"] for skip in report["capital_skips"]] == ["SQZX"]
    with CallDatabase(path) as db:
        assert db.call(kept)["status"] == STATUS_OPEN
