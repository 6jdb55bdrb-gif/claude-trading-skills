"""Rotation requires the newcomer's confidence to be HIGHER. Strictly.

The operator's rule: "only rotate capital if the confidence is higher". Equal
is not higher — a coin toss is not a reason to sell one position and buy
another — so the comparison is strict, and it is enforced separately from the
numeric margin so that setting the margin to zero cannot smuggle in a tie.
"""

from rotation import pick_displacement, rotation_settings

from conftest import review_payload


def _candidate(ticker="OLD", confidence=60, pnl=-8.0):
    return {
        "call_id": 1,
        "ticker": ticker,
        "kind": "shadow",
        "pnl_pct": pnl,
        "confidence": confidence,
        "allocation_usd": 100.0,
        "value_usd": 92.0,
    }


def test_the_shipped_rule_is_strictly_higher_with_no_margin(config):
    settings = rotation_settings(config)
    assert settings["require_higher_confidence"] is True
    assert settings["min_confidence_edge"] == 0


def test_higher_displaces(config):
    pick = pick_displacement(
        review_payload("NEW", confidence=61), [_candidate(confidence=60)], rotation_settings(config)
    )
    assert pick is not None


def test_equal_does_not(config):
    assert (
        pick_displacement(
            review_payload("NEW", confidence=60),
            [_candidate(confidence=60)],
            rotation_settings(config),
        )
        is None
    )


def test_lower_does_not(config):
    assert (
        pick_displacement(
            review_payload("NEW", confidence=59),
            [_candidate(confidence=60)],
            rotation_settings(config),
        )
        is None
    )


def test_a_margin_can_still_be_required_on_top(config):
    settings = {**rotation_settings(config), "min_confidence_edge": 10}
    assert (
        pick_displacement(review_payload("A", confidence=65), [_candidate(confidence=60)], settings)
        is None
    )
    assert (
        pick_displacement(review_payload("B", confidence=70), [_candidate(confidence=60)], settings)
        is not None
    )


def test_the_strict_rule_survives_a_zero_margin(config):
    """The reason this is two settings and not one: `min_confidence_edge: 0`
    alone would read "a difference of at least nothing", which is a tie."""
    settings = {**rotation_settings(config), "min_confidence_edge": 0}
    assert (
        pick_displacement(review_payload("A", confidence=60), [_candidate(confidence=60)], settings)
        is None
    )


def test_a_position_with_no_confidence_is_displaceable_by_anyone(config):
    """An unjudged position has no conviction to beat. Treating "unknown" as
    unbeatable would make the oldest unreviewed rows permanent."""
    pick = pick_displacement(
        review_payload("NEW", confidence=1),
        [_candidate(confidence=None)],
        rotation_settings(config),
    )
    assert pick is not None
