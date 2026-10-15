"""Ten open positions, and no eleventh.

The operator's rule: "only accept 10 open positions at a time as total
portfolio is allocated then". At `position_pct: 10` ten slices ARE the whole
account, so the cap and the cash say the same thing — but only while every
position is a full slice. A part slice (the last one funded, or one funded out
of a rotation) leaves cash behind, and without a count the book would open an
eleventh position on it. The cap is the rule; the cash is a coincidence.

A full book is not a closed door: a new TAKE may still displace a position,
and rotation now fires on a full COUNT as well as on empty cash.
"""

from allocation import open_positions, position_cap
from rotation import rotate_for, rotation_settings

from conftest import review_payload


def _cfg(config, **rotation):
    merged = {**rotation_settings(config), **rotation}
    return {**config, "tracker": {**config["tracker"], "rotation": merged}}


def _fund(db, ticker, *, confidence=40, allocation=100.0, decision="TAKE"):
    return db.insert_call(
        review_payload(ticker, decision=decision, confidence=confidence, entry=10.0),
        run_id="r1",
        allocation_usd=allocation,
    )


def _mark(db, ticker, price):
    db.apply_price(
        db.open_call_for(ticker)["id"], price, close_threshold_pct=None, allow_stop=False
    )


# --- the shipped number -------------------------------------------------


def test_the_cap_is_ten(config):
    assert config["tracker"]["max_open_positions"] == 10
    assert position_cap(config) == 10


def test_the_cap_matches_the_slice_size_it_was_derived_from(config):
    """If these ever disagree, one of them is wrong: 10 x 10% is the account."""
    assert position_cap(config) * config["tracker"]["position_pct"] == 100


# --- counting -----------------------------------------------------------


def test_only_funded_positions_count(tmp_db, config):
    """An unfunded call holds no money, so it cannot be occupying a slot that
    exists because the money runs out. Six legacy rows like this were open
    when the cap went in; letting them block new calls would be the parallel
    book again, from the other direction."""
    _fund(tmp_db, "PAID")
    _fund(tmp_db, "FREE", allocation=None)
    assert open_positions(tmp_db, config) == 1


def test_a_part_slice_still_occupies_a_slot(tmp_db, config):
    _fund(tmp_db, "PART", allocation=12.34)
    assert open_positions(tmp_db, config) == 1


def test_a_closed_position_frees_its_slot(tmp_db, config):
    _fund(tmp_db, "DONE")
    tmp_db.close_call(tmp_db.open_call_for("DONE")["id"], reason="test")
    assert open_positions(tmp_db, config) == 0


# --- rotation fires on a full count, not only on empty cash -------------


def test_a_full_count_with_cash_in_hand_still_rotates(tmp_db, config):
    """The case the count exists for: ten positions and $200 free, because two
    were part slices. Cash alone would have opened an eleventh."""
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40, allocation=80.0)
    _mark(tmp_db, "T3", 7.0)

    rotations = rotate_for(
        tmp_db, _cfg(config), review=review_payload("NEW", confidence=90), run_id="r2"
    )
    assert [entry["ticker"] for entry in rotations] == ["T3"]
    assert open_positions(tmp_db, config) == 9


def test_a_book_under_the_cap_with_cash_does_not_rotate(tmp_db, config):
    for index in range(5):
        _fund(tmp_db, f"T{index}", confidence=40)
    _mark(tmp_db, "T3", 7.0)
    assert (
        rotate_for(tmp_db, _cfg(config), review=review_payload("NEW", confidence=90), run_id="r2")
        == []
    )


def test_a_full_count_rotates_exactly_one_slot_free(tmp_db, config):
    """One slot, not three: the cap is the constraint, so one close answers it
    and the budget is left for the next call."""
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40, allocation=80.0)
    for ticker in ("T1", "T2", "T3"):
        _mark(tmp_db, ticker, 7.0)

    budget = {"used": 0}
    rotations = rotate_for(
        tmp_db,
        _cfg(config),
        review=review_payload("NEW", confidence=90),
        run_id="r2",
        budget=budget,
    )
    assert len(rotations) == 1
    assert budget["used"] == 1


# --- the cycle ----------------------------------------------------------


def test_an_eleventh_call_is_not_made(tmp_path, config):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from call_db import CallDatabase
    from run_cycle import format_report, run_cycle

    from conftest import FIXTURE_HITS

    path = tmp_path / "calls.db"
    with CallDatabase(path) as db:
        # Ten positions, all slightly UP, so none may be displaced — and $200
        # of cash, so only the count can refuse the eleventh.
        for index in range(10):
            _fund(db, f"T{index}", confidence=40, allocation=80.0)
            db.apply_price(
                db.open_call_for(f"T{index}")["id"],
                11.0,
                close_threshold_pct=None,
                allow_stop=False,
            )

    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        now=datetime(2026, 10, 7, 17, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        force_screen=True,
        offline=True,
        db_path=str(path),
        telegram=False,
        prices={},
    )

    assert report["new_calls"] == []
    assert [skip["ticker"] for skip in report["capital_skips"]] == ["SQZX"]
    assert "10 open positions" in report["capital_skips"][0]["reason"]
    assert "10 open positions" in format_report(report)
    with CallDatabase(path) as db:
        assert db.open_call_for("SQZX") is None
