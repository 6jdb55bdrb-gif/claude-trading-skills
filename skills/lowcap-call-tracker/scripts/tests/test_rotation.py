"""Capital rotation: the money and the calls are one book, not two.

The operator's words: "there are too many calls for the allocated money. The
money should rotate — positions should be closed to get the cash to put into
other calls. The $ should be managed also with the calls, not in parallel."

Two mechanisms carry that, and they are deliberately separate:

* **Rotation** — when a new TAKE cannot be funded, the worst open position is
  closed and its cash funds the TAKE. This spends real money, so every rule
  below is a brake: only a TAKE may displace, a winner is never displaced, the
  newcomer must beat the position it replaces by a margin, and a run may only
  rotate a few times.
* **The capital gate** — a call that still cannot be funded after rotation is
  not made at all. It used to be logged with no money, which read in the
  report exactly like a funded call: that is the parallel book the operator
  objected to.
"""

import pytest
from allocation import full_slice_usd, portfolio_state
from rotation import (
    capital_gated,
    displaceable,
    pick_displacement,
    rotate_for,
    rotation_settings,
)

from conftest import review_payload


def _cfg(config, **rotation):
    merged = {**rotation_settings(config), **rotation}
    return {**config, "tracker": {**config["tracker"], "rotation": merged}}


def _fund(db, ticker, *, decision="TAKE", confidence=70, entry=10.0, allocation=100.0):
    return db.insert_call(
        review_payload(ticker, decision=decision, confidence=confidence, entry=entry),
        run_id="r1",
        allocation_usd=allocation,
    )


def _mark(db, call_id, price):
    db.apply_price(call_id, price, close_threshold_pct=None, allow_stop=False)


# --- the shipped policy -------------------------------------------------


def test_rotation_is_on_and_gated_by_default(config):
    """Pinned on the shipped config, not on the module's own fallbacks: the
    defaults in rotation.py exist for a partial config, and a test that reads
    them would pass with the YAML block deleted."""
    tracker = config["tracker"]
    assert tracker["capital_gated"] is True
    assert tracker["rotation"] == {
        "enabled": True,
        "require_take": True,
        "protect_winners": True,
        "max_displace_pnl_pct": 0.0,
        "min_confidence_edge": 10,
        "max_per_run": 3,
        "min_fill_fraction": 0.8,
    }
    assert rotation_settings(config) == tracker["rotation"]
    assert capital_gated(config) is True


def test_a_partial_rotation_block_keeps_the_conservative_defaults(config):
    partial = {**config, "tracker": {**config["tracker"], "rotation": {"max_per_run": 1}}}
    settings = rotation_settings(partial)
    assert settings["max_per_run"] == 1
    assert settings["require_take"] is True
    assert settings["protect_winners"] is True


# --- who may be displaced ----------------------------------------------


def test_the_worst_loser_is_first_in_line(tmp_db, config):
    mild = _fund(tmp_db, "MILD", confidence=40)
    bad = _fund(tmp_db, "BAD", confidence=40)
    _mark(tmp_db, mild, 9.5)
    _mark(tmp_db, bad, 7.0)

    assert [row["ticker"] for row in displaceable(tmp_db, config)] == ["BAD", "MILD"]


def test_a_winner_is_never_displaced(tmp_db, config):
    """A rotation rule that sells winners to buy screener hits is a machine
    for turning a good book into a bad one."""
    won = _fund(tmp_db, "WON", confidence=20)
    _mark(tmp_db, won, 18.0)
    assert displaceable(tmp_db, config) == []


def test_a_flat_position_is_not_displaced_either(tmp_db, config):
    """max_displace_pnl_pct is 0, and a position at 0.0% has not failed."""
    flat = _fund(tmp_db, "FLAT", confidence=20)
    _mark(tmp_db, flat, 10.0)
    assert displaceable(tmp_db, config) == []


def test_an_unfunded_call_is_not_a_source_of_cash(tmp_db, config):
    """It never spent anything, so closing it frees nothing."""
    empty = _fund(tmp_db, "EMPTY", allocation=None)
    _mark(tmp_db, empty, 5.0)
    assert displaceable(tmp_db, config) == []


def test_a_closed_call_is_not_displaceable(tmp_db, config):
    done = _fund(tmp_db, "DONE")
    _mark(tmp_db, done, 8.0)
    tmp_db.close_call(done, reason="test")
    assert displaceable(tmp_db, config) == []


# --- who may displace ---------------------------------------------------


def test_only_a_take_may_displace(tmp_db, config):
    loser = _fund(tmp_db, "BAD", confidence=20)
    _mark(tmp_db, loser, 7.0)
    candidates = displaceable(tmp_db, config)

    skip = review_payload("NEW", decision="SKIP", confidence=90)
    assert pick_displacement(skip, candidates, rotation_settings(config)) is None

    take = review_payload("NEW", decision="TAKE", confidence=90)
    assert pick_displacement(take, candidates, rotation_settings(config))["ticker"] == "BAD"


def test_the_newcomer_must_beat_the_position_it_replaces(tmp_db, config):
    loser = _fund(tmp_db, "BAD", confidence=70)
    _mark(tmp_db, loser, 7.0)
    candidates = displaceable(tmp_db, config)
    settings = rotation_settings(config)

    # 75 against 70 is noise, not an edge: the required margin is 10.
    assert pick_displacement(review_payload("A", confidence=75), candidates, settings) is None
    assert pick_displacement(review_payload("B", confidence=80), candidates, settings) is not None


def test_a_newcomer_without_a_confidence_never_displaces(tmp_db, config):
    """An unjudged hit has no claim on money that is already committed."""
    from call_db import DECISION_UNREVIEWED

    loser = _fund(tmp_db, "BAD", confidence=20)
    _mark(tmp_db, loser, 7.0)
    pending = review_payload("NEW", decision=DECISION_UNREVIEWED, confidence=None)
    settings = {**rotation_settings(config), "require_take": False}
    assert pick_displacement(pending, displaceable(tmp_db, config), settings) is None


# --- the rotation itself ------------------------------------------------


def test_rotation_closes_the_loser_and_frees_its_value(tmp_db, config):
    """$100 in at 10.00, marked 7.00, is $70 of cash — not $100. Freeing the
    allocation rather than the value would invent $30."""
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    loser = tmp_db.open_call_for("T3")["id"]
    _mark(tmp_db, loser, 7.0)
    assert portfolio_state(tmp_db, config)["cash_usd"] == pytest.approx(0.0, abs=0.01)

    rotations = rotate_for(
        tmp_db,
        _cfg(config),
        review=review_payload("NEW", confidence=90),
        run_id="r2",
    )

    assert [entry["ticker"] for entry in rotations] == ["T3"]
    assert rotations[0]["freed_usd"] == pytest.approx(70.0, abs=0.01)
    assert rotations[0]["for_ticker"] == "NEW"
    assert tmp_db.call(loser)["status"] != "open"
    assert "rotated out" in tmp_db.call(loser)["close_reason"]
    assert "NEW" in tmp_db.call(loser)["close_reason"]
    assert portfolio_state(tmp_db, config)["cash_usd"] == pytest.approx(70.0, abs=0.01)


def test_nothing_rotates_while_there_is_cash(tmp_db, config):
    _fund(tmp_db, "BAD", confidence=20)
    _mark(tmp_db, tmp_db.open_call_for("BAD")["id"], 7.0)
    assert (
        rotate_for(tmp_db, _cfg(config), review=review_payload("NEW", confidence=90), run_id="r2")
        == []
    )


def test_rotation_stops_once_a_full_slice_is_free(tmp_db, config):
    """One loser at -30% frees $70 of a $100 slice, which is under the 80%
    fill floor; a second takes it past it and a third is not taken."""
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    for ticker in ("T1", "T2", "T3"):
        _mark(tmp_db, tmp_db.open_call_for(ticker)["id"], 7.0)

    rotations = rotate_for(
        tmp_db, _cfg(config), review=review_payload("NEW", confidence=90), run_id="r2"
    )
    assert len(rotations) == 2
    assert portfolio_state(tmp_db, config)["cash_usd"] >= full_slice_usd(config)


def test_a_second_position_is_not_closed_to_cover_a_rounding_shortfall(tmp_db, config):
    """The live failure this rule exists for.

    On 2026-10-14 TCRT displaced BTCS, which freed $89.63 of a $100 slice —
    and the loop closed IMMR as well, a position only 2.1% down, for the
    remaining $10.37. Closing a near-flat position to top another up by a
    tenth of a slice is exactly the churn every other brake here prevents.
    Worse, the money went to the NEXT call in the run while the close reason
    named this one, so the record misattributed it.

    A rotation now stops once the cash covers `min_fill_fraction` of a slice.
    The next call rotates for itself, under its own name."""
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    _mark(tmp_db, tmp_db.open_call_for("T1")["id"], 8.96)  # -10.4%, frees $89.60
    _mark(tmp_db, tmp_db.open_call_for("T2")["id"], 9.79)  # -2.1%, barely down

    rotations = rotate_for(
        tmp_db, _cfg(config), review=review_payload("NEW", confidence=90), run_id="r2"
    )

    assert [entry["ticker"] for entry in rotations] == ["T1"]
    assert tmp_db.open_call_for("T2") is not None, "a near-flat position was churned"
    # 89.6% of a slice, funded as a part slice rather than paid for twice.
    assert portfolio_state(tmp_db, config)["cash_usd"] == pytest.approx(89.60, abs=0.01)


def test_the_fill_floor_is_configurable_and_shipped_at_80_percent(config):
    assert config["tracker"]["rotation"]["min_fill_fraction"] == 0.8
    assert rotation_settings(config)["min_fill_fraction"] == 0.8


def test_a_fill_floor_of_one_restores_the_strict_full_slice_rule(tmp_db, config):
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    _mark(tmp_db, tmp_db.open_call_for("T1")["id"], 8.96)
    _mark(tmp_db, tmp_db.open_call_for("T2")["id"], 9.79)

    rotations = rotate_for(
        tmp_db,
        _cfg(config, min_fill_fraction=1.0),
        review=review_payload("NEW", confidence=90),
        run_id="r2",
    )
    assert [entry["ticker"] for entry in rotations] == ["T1", "T2"]


def test_a_run_may_only_rotate_so_many_times(tmp_db, config):
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    for index in range(10):
        _mark(tmp_db, tmp_db.open_call_for(f"T{index}")["id"], 1.0)

    budget = {"used": 0}
    rotations = rotate_for(
        tmp_db,
        _cfg(config, max_per_run=2),
        review=review_payload("NEW", confidence=90),
        run_id="r2",
        budget=budget,
    )
    # Each -90% position frees $10, so a $100 slice would eat the whole book.
    assert len(rotations) == 2
    assert budget["used"] == 2


def test_the_budget_is_shared_across_calls_in_one_run(tmp_db, config):
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    for index in range(10):
        _mark(tmp_db, tmp_db.open_call_for(f"T{index}")["id"], 1.0)

    budget = {"used": 0}
    cfg = _cfg(config, max_per_run=2)
    first = rotate_for(
        tmp_db, cfg, review=review_payload("A", confidence=90), run_id="r2", budget=budget
    )
    second = rotate_for(
        tmp_db, cfg, review=review_payload("B", confidence=90), run_id="r2", budget=budget
    )
    assert len(first) == 2
    assert second == []


def test_rotation_can_be_switched_off(tmp_db, config):
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    _mark(tmp_db, tmp_db.open_call_for("T3")["id"], 7.0)
    assert (
        rotate_for(
            tmp_db,
            _cfg(config, enabled=False),
            review=review_payload("NEW", confidence=90),
            run_id="r2",
        )
        == []
    )


def test_a_rotation_never_displaces_the_same_ticker(tmp_db, config):
    """A name already open is a duplicate, not a rotation target."""
    for index in range(10):
        _fund(tmp_db, f"T{index}", confidence=40)
    _mark(tmp_db, tmp_db.open_call_for("T3")["id"], 7.0)
    rotations = rotate_for(
        tmp_db, _cfg(config), review=review_payload("T3", confidence=90), run_id="r2"
    )
    assert rotations == []
