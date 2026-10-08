"""v2 post-screen guards: the change cap, the short-float bonus, the run gate.

v2 widened the FinViz filters deliberately: a hard ``sh_short_o15`` floor threw
away names on short data FinViz refreshes twice a month, and a hard float cap
threw away the mid-float names that squeeze hardest. What the filters stopped
rejecting, these guards weigh instead.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from screener_guards import (
    apply_change_cap,
    apply_short_float_bonus,
    change_cap,
    earliest_run_block,
    hit_version,
    short_float_points,
)


@pytest.fixture()
def v2(config):
    config["screener"]["screener_version"] = "v2"
    return config


# --- the change cap -------------------------------------------------------


def test_v2_caps_the_days_move_at_25_percent(v2):
    assert change_cap(v2) == 25.0


def test_v1_has_no_change_cap(config):
    assert change_cap(config) is None


def test_a_name_already_up_30_percent_is_skipped(v2):
    hits = [
        {"ticker": "CALM", "change_pct": 8.0},
        {"ticker": "GONE", "change_pct": 30.0},
    ]
    kept, skipped = apply_change_cap(hits, v2)
    assert [hit["ticker"] for hit in kept] == ["CALM"]
    assert skipped[0]["ticker"] == "GONE"
    assert skipped[0]["change_pct"] == 30.0
    assert "25" in skipped[0]["reason"]


def test_the_cap_is_inclusive_of_the_boundary(v2):
    """ "up more than +25%" — exactly +25% still trades."""
    kept, skipped = apply_change_cap([{"ticker": "EDGE", "change_pct": 25.0}], v2)
    assert [hit["ticker"] for hit in kept] == ["EDGE"]
    assert skipped == []


def test_a_name_down_hard_is_not_capped(v2):
    """The cap exists to refuse chasing, so it reads one side only."""
    kept, _ = apply_change_cap([{"ticker": "DUMP", "change_pct": -40.0}], v2)
    assert [hit["ticker"] for hit in kept] == ["DUMP"]


def test_an_unknown_move_is_kept_not_guessed(v2):
    """A missing change column is a data gap; the roles still get to look."""
    kept, skipped = apply_change_cap(
        [{"ticker": "QUIET"}, {"ticker": "ODD", "change_pct": "n/a"}], v2
    )
    assert {hit["ticker"] for hit in kept} == {"QUIET", "ODD"}
    assert skipped == []


def test_v1_hits_pass_the_cap_untouched(config):
    hits = [{"ticker": "RIP", "change_pct": 80.0}]
    kept, skipped = apply_change_cap(hits, config)
    assert kept == hits
    assert skipped == []


def test_the_cap_follows_the_version_that_produced_the_hit(config):
    """A v1 call reviewed during a v2 run is judged by v1's rules."""
    hits = [{"ticker": "OLD", "change_pct": 80.0, "screener_version": "v1"}]
    config["screener"]["screener_version"] = "v2"
    kept, skipped = apply_change_cap(hits, config)
    assert [hit["ticker"] for hit in kept] == ["OLD"]
    assert skipped == []


# --- the short-float bonus ------------------------------------------------


@pytest.mark.parametrize(
    ("short_float_pct", "points"),
    [
        (None, 0),
        (0.0, 0),
        (9.9, 0),
        (10.0, 5),
        (15.0, 5),
        (19.99, 5),
        (20.0, 10),
        (41.0, 10),
    ],
)
def test_the_bonus_rungs(v2, short_float_pct, points):
    assert short_float_points({"short_float_pct": short_float_pct}, v2) == points


def test_the_bonus_is_not_cumulative_across_rungs(v2):
    """A 25% short float earns the 20% rung, not 20% plus 10%."""
    assert short_float_points({"short_float_pct": 25.0}, v2) == 10


def test_v1_awards_no_bonus_because_it_filters_on_short_float_instead(config):
    assert short_float_points({"short_float_pct": 30.0}, config) == 0


def test_percent_strings_from_the_ownership_view_are_read(v2):
    assert short_float_points({"short_float_pct": "22.4%"}, v2) == 10


def test_the_bonus_lifts_a_judges_confidence(v2):
    verdict = {"decision": "SKIP", "confidence": 52}
    out = apply_short_float_bonus(verdict, {"short_float_pct": 21.0}, v2)
    assert out["confidence"] == 62
    assert out["short_float_bonus"]["points"] == 10
    assert out["short_float_bonus"]["confidence_before"] == 52
    assert out["short_float_bonus"]["short_float_pct"] == 21.0


def test_the_bonus_cannot_push_confidence_past_100(v2):
    out = apply_short_float_bonus(
        {"decision": "TAKE", "confidence": 95}, {"short_float_pct": 30.0}, v2
    )
    assert out["confidence"] == 100


def test_no_short_float_leaves_the_verdict_exactly_as_it_was(v2):
    verdict = {"decision": "SKIP", "confidence": 40}
    out = apply_short_float_bonus(dict(verdict), {"ticker": "NONE"}, v2)
    assert out == verdict


def test_the_bonus_never_silently_rewrites_the_decision(v2):
    """The bonus moves confidence; the gate alone decides TAKE vs SKIP."""
    out = apply_short_float_bonus(
        {"decision": "SKIP", "confidence": 52}, {"short_float_pct": 21.0}, v2
    )
    assert out["decision"] == "SKIP"


# --- the run gate ---------------------------------------------------------


def _zurich(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 7, hour, minute, tzinfo=ZoneInfo("Europe/Zurich"))


def test_v2_will_not_screen_before_eight_zurich(v2):
    block = earliest_run_block(v2, now=_zurich(7, 45))
    assert block is not None
    assert "08:00" in block
    assert "Europe/Zurich" in block


def test_v2_screens_from_eight_zurich(v2):
    """The operator's floor. The market's own extended-hours window is a
    separate, later constraint, so this alone does not mean a 2am screen."""
    assert earliest_run_block(v2, now=_zurich(8, 0)) is None
    assert earliest_run_block(v2, now=_zurich(16, 30)) is None
    assert earliest_run_block(v2, now=_zurich(21, 0)) is None


def test_v1_has_no_run_gate(config):
    assert earliest_run_block(config, now=_zurich(9, 0)) is None


def test_the_gate_reads_zurich_not_the_hosts_clock(v2):
    """A VPS in UTC runs two hours behind Zurich in summer: 06:30 UTC is 08:30
    Zurich and must be allowed, while 07:00 Zurich must not."""
    assert earliest_run_block(v2, now=datetime(2026, 7, 1, 6, 30, tzinfo=ZoneInfo("UTC"))) is None
    assert (
        earliest_run_block(v2, now=datetime(2026, 7, 1, 5, 0, tzinfo=ZoneInfo("UTC"))) is not None
    )


def test_a_naive_timestamp_is_read_as_zurich_local(v2):
    assert earliest_run_block(v2, now=datetime(2026, 10, 7, 8, 45)) is None
    assert earliest_run_block(v2, now=datetime(2026, 10, 7, 3, 0)) is not None


# --- version attribution --------------------------------------------------


def test_a_hit_carries_the_version_that_produced_it(v2):
    assert hit_version({"ticker": "NEW"}, v2) == "v2"
    assert hit_version({"ticker": "OLD", "screener_version": "v1"}, v2) == "v1"


# --- wiring ---------------------------------------------------------------

FIXTURE = "fixtures/dry_run_hits.json"


def test_every_hit_is_tagged_with_the_version_that_screened_it(v2):
    from fetch_screener import screen_all

    hits = screen_all(v2, mode="fixture", fixture=FIXTURE)
    assert hits
    assert {hit["screener_version"] for hit in hits} == {"v2"}


def test_screening_drops_the_capped_name_and_reports_it(v2):
    """PMPX is +41% on the fixture day: v2 refuses to chase it, v1 does not."""
    from fetch_screener import screen_all

    skips: list[dict] = []
    tickers = [
        hit["ticker"] for hit in screen_all(v2, mode="fixture", fixture=FIXTURE, guard_skips=skips)
    ]
    assert "PMPX" not in tickers
    assert [skip["ticker"] for skip in skips] == ["PMPX"]
    assert "41" in skips[0]["reason"]


def test_v1_still_screens_the_same_three_names(config):
    from fetch_screener import screen_all

    skips: list[dict] = []
    tickers = {
        hit["ticker"]
        for hit in screen_all(config, mode="fixture", fixture=FIXTURE, guard_skips=skips)
    }
    assert tickers == {"SQZX", "PMPX", "URAX"}
    assert skips == []


def test_the_bonus_reaches_the_judge_before_the_gate(v2):
    """SQZX carries a 28.4% short float, so a v2 review records the 10 points."""
    from role_review import review_hit

    hit = {
        "ticker": "SQZX",
        "asset_type": "stock",
        "variant": "squeeze",
        "price": 3.8,
        "short_float_pct": 28.4,
        "screener_version": "v2",
    }
    review = review_hit(hit, v2, backend="heuristic", offline=True)
    bonus = review["verdicts"]["judge"]["short_float_bonus"]
    assert bonus["points"] == 10
    assert bonus["confidence_after"] == min(100, bonus["confidence_before"] + 10)
    assert review["confidence"] == bonus["confidence_after"]


def test_a_v1_review_of_the_same_name_records_no_bonus(config):
    from role_review import review_hit

    hit = {
        "ticker": "SQZX",
        "asset_type": "stock",
        "variant": "squeeze",
        "price": 3.8,
        "short_float_pct": 28.4,
        "screener_version": "v1",
    }
    review = review_hit(hit, config, backend="heuristic", offline=True)
    assert "short_float_bonus" not in review["verdicts"]["judge"]
