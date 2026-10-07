"""The v1-vs-v2 scorecard, and the recommendations it is allowed to make.

Nothing in here changes a threshold. The report says what the numbers are and
what it would propose; the operator decides. That boundary is the whole reason
the loop is safe to run unattended.
"""

import pytest
from outcome_report import (
    CONFIDENCE_BUCKETS,
    bucket_for,
    build_report,
    recommendations,
    render_report,
)

from conftest import review_payload


def add_call(
    db,
    ticker,
    *,
    version,
    variant="squeeze",
    decision="TAKE",
    confidence=70,
    ret=10.0,
    stopped=False,
    researcher=7.0,
    entry=10.0,
    date="2026-10-07",
):
    payload = review_payload(
        ticker,
        decision=decision,
        confidence=confidence,
        entry=entry,
        variant=variant,
        scores=(researcher, 6.0, 3.0, 6.0),
    )
    payload["hit"] = {"ticker": ticker, "screener_version": version}
    call_id = db.insert_call(payload, run_id="r1", now=f"{date}T20:00:00+00:00", sl_pct=20.0)
    db.conn.execute(
        "UPDATE calls SET ret_1d = ?, ret_3d = ?, ret_5d = ?, stopped_out = ?, "
        "outcome_updated_at = '2026-10-15T00:00:00+00:00' WHERE id = ?",
        (ret, ret, ret, 1 if stopped else 0, call_id),
    )
    db.conn.commit()
    return call_id


# --- buckets --------------------------------------------------------------


@pytest.mark.parametrize(
    ("confidence", "label"),
    [
        (0, "<50"),
        (49, "<50"),
        (50, "50-59"),
        (59, "50-59"),
        (60, "60-69"),
        (69, "60-69"),
        (70, "70+"),
        (95, "70+"),
        (None, "unknown"),
    ],
)
def test_confidence_buckets(confidence, label):
    assert bucket_for(confidence) == label


def test_the_buckets_the_spec_asked_for_are_all_present():
    assert {"50-59", "60-69", "70+"} <= set(CONFIDENCE_BUCKETS)


# --- the per-version numbers ---------------------------------------------


def test_each_version_is_scored_separately(tmp_db, config):
    add_call(tmp_db, "AONE", version="v1", ret=20.0)
    add_call(tmp_db, "ATWO", version="v1", ret=-10.0)
    add_call(tmp_db, "BONE", version="v2", ret=30.0)
    report = build_report(tmp_db, config)
    v1 = report["versions"]["v1"]
    v2 = report["versions"]["v2"]
    assert v1["calls"] == 2 and v2["calls"] == 1
    assert v1["hit_rate_pct"] == 50.0
    assert v1["avg_return_pct"] == 5.0
    assert v2["avg_return_pct"] == 30.0


def test_hit_rate_counts_a_positive_settled_return(tmp_db, config):
    add_call(tmp_db, "FLAT", version="v2", ret=0.0)
    add_call(tmp_db, "UP", version="v2", ret=0.1)
    report = build_report(tmp_db, config)
    assert report["versions"]["v2"]["hit_rate_pct"] == 50.0


def test_stop_hit_rate_is_reported_per_version(tmp_db, config):
    add_call(tmp_db, "OUT1", version="v2", ret=-20.0, stopped=True)
    add_call(tmp_db, "OK1", version="v2", ret=5.0)
    add_call(tmp_db, "OK2", version="v2", ret=5.0)
    add_call(tmp_db, "OK3", version="v2", ret=5.0)
    assert build_report(tmp_db, config)["versions"]["v2"]["stop_hit_rate_pct"] == 25.0


def test_variants_are_broken_out_within_a_version(tmp_db, config):
    add_call(tmp_db, "SQ1", version="v2", variant="squeeze", ret=10.0)
    add_call(tmp_db, "MB1", version="v2", variant="momentum_breakout", ret=-30.0, stopped=True)
    variants = build_report(tmp_db, config)["versions"]["v2"]["variants"]
    assert variants["squeeze"]["avg_return_pct"] == 10.0
    assert variants["momentum_breakout"]["stop_hit_rate_pct"] == 100.0


def test_confidence_buckets_are_broken_out_within_a_version(tmp_db, config):
    add_call(tmp_db, "LOW1", version="v2", confidence=55, ret=-15.0)
    add_call(tmp_db, "MID1", version="v2", confidence=65, ret=5.0)
    add_call(tmp_db, "HIGH1", version="v2", confidence=80, ret=25.0)
    buckets = build_report(tmp_db, config)["versions"]["v2"]["buckets"]
    assert buckets["50-59"]["avg_return_pct"] == -15.0
    assert buckets["60-69"]["avg_return_pct"] == 5.0
    assert buckets["70+"]["avg_return_pct"] == 25.0


def test_takes_and_skips_are_scored_side_by_side(tmp_db, config):
    """The Judge's edge is the gap between what it took and what it refused."""
    add_call(tmp_db, "TK1", version="v2", decision="TAKE", ret=10.0)
    add_call(tmp_db, "SK1", version="v2", decision="SKIP", ret=40.0)
    decisions = build_report(tmp_db, config)["versions"]["v2"]["decisions"]
    assert decisions["TAKE"]["avg_return_pct"] == 10.0
    assert decisions["SKIP"]["avg_return_pct"] == 40.0
    assert build_report(tmp_db, config)["versions"]["v2"]["judge_edge_pct"] == -30.0


def test_a_call_with_no_elapsed_horizon_is_counted_as_pending_not_as_a_loss(tmp_db, config):
    add_call(tmp_db, "RIPE", version="v2", ret=10.0)
    fresh = add_call(tmp_db, "FRESH", version="v2", ret=10.0)
    tmp_db.conn.execute(
        "UPDATE calls SET ret_1d = NULL, ret_3d = NULL, ret_5d = NULL WHERE id = ?", (fresh,)
    )
    tmp_db.conn.commit()
    report = build_report(tmp_db, config)
    assert report["versions"]["v2"]["calls"] == 1
    assert report["pending"] == 1


def test_an_empty_book_reports_nothing_rather_than_dividing_by_zero(tmp_db, config):
    report = build_report(tmp_db, config)
    assert report["total_calls"] == 0
    assert report["versions"] == {}
    assert "no measured calls yet" in render_report(report).lower()


# --- the telegram gate ---------------------------------------------------


def test_the_report_stays_out_of_telegram_until_thirty_calls(tmp_db, config):
    for index in range(29):
        add_call(tmp_db, f"T{index}", version="v2", ret=5.0)
    report = build_report(tmp_db, config)
    assert report["total_calls"] == 29
    assert report["telegram_ready"] is False


def test_thirty_calls_opens_the_telegram_summary(tmp_db, config):
    for index in range(30):
        add_call(tmp_db, f"T{index}", version="v2", ret=5.0)
    assert build_report(tmp_db, config)["telegram_ready"] is True


# --- recommendations, never applied --------------------------------------


def test_a_losing_low_confidence_bucket_proposes_a_higher_threshold(tmp_db, config):
    for index in range(6):
        add_call(tmp_db, f"L{index}", version="v2", confidence=55, ret=-18.0)
    for index in range(6):
        add_call(tmp_db, f"H{index}", version="v2", confidence=75, ret=22.0)
    proposals = recommendations(build_report(tmp_db, config), config)
    threshold = [item for item in proposals if item["setting"].endswith("min_confidence_to_take")]
    assert threshold, "a losing bucket below the threshold should be raised"
    assert threshold[0]["current"] == config["roles"]["judge"]["min_confidence_to_take"]
    assert threshold[0]["proposed"] == 60
    assert threshold[0]["applied"] is False


def test_nothing_is_proposed_without_enough_samples(tmp_db, config):
    add_call(tmp_db, "ONE", version="v2", confidence=55, ret=-30.0)
    assert recommendations(build_report(tmp_db, config), config) == []


def test_a_bucket_that_pays_is_left_alone(tmp_db, config):
    for index in range(8):
        add_call(tmp_db, f"G{index}", version="v2", confidence=55, ret=12.0)
    proposals = recommendations(build_report(tmp_db, config), config)
    assert [item for item in proposals if "min_confidence_to_take" in item["setting"]] == []


def test_a_catalyst_gap_proposes_a_penalty_change(tmp_db, config):
    """Calls the Researcher found nothing for should underperform, or the
    penalty is charging for nothing."""
    for index in range(6):
        add_call(tmp_db, f"C{index}", version="v2", researcher=8.0, ret=20.0)
    for index in range(6):
        add_call(tmp_db, f"N{index}", version="v2", researcher=1.0, ret=-20.0)
    proposals = recommendations(build_report(tmp_db, config), config)
    penalty = [item for item in proposals if item["setting"].endswith("no_catalyst_penalty")]
    assert penalty
    assert penalty[0]["proposed"] > penalty[0]["current"]
    assert penalty[0]["applied"] is False


def test_no_recommendation_ever_touches_the_config(tmp_db, config):
    for index in range(6):
        add_call(tmp_db, f"L{index}", version="v2", confidence=55, ret=-18.0)
    for index in range(6):
        add_call(tmp_db, f"H{index}", version="v2", confidence=75, ret=22.0)
    before = dict(config["roles"]["judge"])
    report = build_report(tmp_db, config)
    recommendations(report, config)
    render_report(report)
    assert config["roles"]["judge"] == before


def test_the_rendered_report_says_recommendations_are_not_applied(tmp_db, config):
    for index in range(6):
        add_call(tmp_db, f"L{index}", version="v2", confidence=55, ret=-18.0)
    for index in range(6):
        add_call(tmp_db, f"H{index}", version="v2", confidence=75, ret=22.0)
    text = render_report(build_report(tmp_db, config), config=config)
    assert "not applied" in text.lower()
    assert "min_confidence_to_take" in text


# --- rendering -----------------------------------------------------------


def test_the_rendered_report_compares_the_versions(tmp_db, config):
    add_call(tmp_db, "A1", version="v1", ret=-5.0)
    add_call(tmp_db, "B1", version="v2", ret=15.0)
    text = render_report(build_report(tmp_db, config), config=config)
    assert "v1" in text and "v2" in text
    assert "squeeze" in text
    assert "50-59" in text or "70+" in text
