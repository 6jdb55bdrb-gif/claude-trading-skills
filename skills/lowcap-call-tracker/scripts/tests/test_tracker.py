"""Call database, price updates, statistics, learning loop and the run cycle."""

from datetime import datetime, timezone

import pytest
from call_db import KIND_ACTIVE, KIND_SHADOW, STATUS_CLOSED_WRONG, STATUS_OPEN, pnl_pct
from learning_loop import analyse, is_due
from learning_loop import render_markdown as render_improvements
from price_update import update_open_calls
from run_cycle import run_cycle
from stats import compute_stats, outcome, render_markdown, render_text

from conftest import FIXTURE_HITS, review_payload

# ------------------------------------------------------------------- PnL maths


@pytest.mark.parametrize(
    ("entry", "current", "direction", "expected"),
    [
        (200.0, 210.0, "long", 5.0),  # the example from the specification
        (200.0, 190.0, "long", -5.0),
        (200.0, 190.0, "short", 5.0),  # a short gains when price falls
        (200.0, 210.0, "short", -5.0),
        (10.0, 1.0, "long", -90.0),
        (10.0, 20.0, "short", -100.0),
    ],
)
def test_pnl_is_direction_corrected(entry, current, direction, expected):
    assert pnl_pct(entry, current, direction) == pytest.approx(expected)


def test_pnl_guards_bad_input():
    assert pnl_pct(0.0, 10.0, "long") is None
    assert pnl_pct(10.0, None, "long") is None


# -------------------------------------------------------------------- database


def test_insert_stores_every_role_verdict(tmp_db):
    call_id = tmp_db.insert_call(review_payload("AAA"), run_id="r1")
    assert call_id is not None
    verdicts = tmp_db.verdicts_for(call_id)
    assert set(verdicts) == {"researcher", "technician", "skeptic", "risk_manager", "judge"}
    row = tmp_db.call(call_id)
    assert row["kind"] == KIND_ACTIVE
    assert row["status"] == STATUS_OPEN
    assert row["researcher_score"] == 7.0
    assert row["skeptic_score"] == 3.0


def test_skip_is_stored_as_a_shadow_call(tmp_db):
    call_id = tmp_db.insert_call(review_payload("BBB", decision="SKIP", confidence=20), run_id="r1")
    assert tmp_db.call(call_id)["kind"] == KIND_SHADOW


def test_open_ticker_is_never_duplicated(tmp_db):
    assert tmp_db.insert_call(review_payload("AAA"), run_id="r1") is not None
    assert tmp_db.insert_call(review_payload("AAA"), run_id="r2") is None


def test_a_closed_ticker_can_be_called_again(tmp_db, config):
    first = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.apply_price(first, 1.0, close_threshold_pct=-80.0)
    assert tmp_db.call(first)["status"] == STATUS_CLOSED_WRONG
    assert tmp_db.insert_call(review_payload("AAA", entry=2.0), run_id="r2") is not None


def test_price_history_accumulates(tmp_db):
    call_id = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.apply_price(call_id, 11.0, close_threshold_pct=-80.0)
    tmp_db.apply_price(call_id, 12.0, close_threshold_pct=-80.0)
    rows = list(
        tmp_db.conn.execute(
            "SELECT price FROM price_history WHERE call_id = ? ORDER BY id", (call_id,)
        )
    )
    assert [row["price"] for row in rows] == [10.0, 11.0, 12.0]


def test_close_happens_exactly_at_the_threshold(tmp_db):
    call_id = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    result = tmp_db.apply_price(call_id, 2.0, close_threshold_pct=-80.0)  # exactly -80%
    assert result["closed"] is True
    row = tmp_db.call(call_id)
    assert row["status"] == STATUS_CLOSED_WRONG
    assert "threshold" in row["close_reason"]


def test_no_other_auto_close_exists(tmp_db):
    """A deep drawdown short of the threshold stays open; profits never close."""
    call_id = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.apply_price(call_id, 2.1, close_threshold_pct=-80.0)  # -79%
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN
    tmp_db.apply_price(call_id, 100.0, close_threshold_pct=-80.0)  # +900%
    assert tmp_db.call(call_id)["status"] == STATUS_OPEN


def test_threshold_is_taken_from_config(tmp_db, config):
    config["tracker"]["close_threshold_pct"] = -30.0
    call_id = tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    update_open_calls(tmp_db, config, prices={"AAA": 6.5})  # -35%
    assert tmp_db.call(call_id)["status"] == STATUS_CLOSED_WRONG


def test_short_call_closes_on_a_rally(tmp_db, config):
    call_id = tmp_db.insert_call(review_payload("SHRT", entry=2.0, direction="short"), run_id="r1")
    update_open_calls(tmp_db, config, prices={"SHRT": 3.7})  # -85% for a short
    assert tmp_db.call(call_id)["status"] == STATUS_CLOSED_WRONG


# ---------------------------------------------------------------- price update


def test_update_prices_every_open_call_including_shadows(tmp_db, config):
    tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    tmp_db.insert_call(review_payload("BBB", decision="SKIP", entry=5.0), run_id="r1")
    result = update_open_calls(tmp_db, config, prices={"AAA": 11.0, "BBB": 4.0})
    assert result["priced"] == 2
    assert result["closed"] == 0
    pnls = {update["ticker"]: update["pnl_pct"] for update in result["updates"]}
    assert pnls["AAA"] == pytest.approx(10.0)
    assert pnls["BBB"] == pytest.approx(-20.0)


def test_missing_prices_are_reported_not_fatal(tmp_db, config):
    tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    result = update_open_calls(tmp_db, config, prices={})
    assert result["priced"] == 0
    assert result["missing_prices"] == ["AAA"]


# ----------------------------------------------------------------- statistics


def _seed(db, config):
    """Two winners, one stop-out, one open loser, one shadow winner."""
    plan = [
        ("WIN1", "TAKE", 85, 10.0, "squeeze", "stock", "long", 14.0, (9, 8, 1, 7)),
        ("WIN2", "TAKE", 65, 20.0, "etf_momentum", "etf", "long", 22.0, (7, 7, 2, 6)),
        ("LOSE", "TAKE", 60, 10.0, "squeeze", "stock", "long", 1.5, (5, 5, 6, 5)),
        ("FLAT", "TAKE", 58, 4.0, "momentum_breakout", "stock", "short", 4.2, (5, 4, 5, 5)),
        ("SHAD", "SKIP", 30, 5.0, "momentum_breakout", "stock", "long", 6.0, (3, 3, 9, 4)),
    ]
    for ticker, decision, confidence, entry, variant, asset, direction, price, scores in plan:
        call_id = db.insert_call(
            review_payload(
                ticker,
                decision=decision,
                confidence=confidence,
                entry=entry,
                variant=variant,
                asset_type=asset,
                direction=direction,
                scores=scores,
            ),
            run_id="r1",
        )
        db.apply_price(call_id, price, close_threshold_pct=config["tracker"]["close_threshold_pct"])


def test_outcome_classification(tmp_db, config):
    _seed(tmp_db, config)
    rows = {row["ticker"]: row for row in tmp_db.all_calls()}
    assert outcome(rows["WIN1"]) == "RIGHT"
    assert outcome(rows["LOSE"]) == "WRONG"  # closed at the threshold
    assert outcome(rows["FLAT"]) == "NEUTRAL"  # open short, price above entry
    assert rows["LOSE"]["status"] == STATUS_CLOSED_WRONG


def test_overall_statistics(tmp_db, config):
    _seed(tmp_db, config)
    stats = compute_stats(tmp_db, config)
    overall = stats["overall"]
    assert overall["total"] == 5
    assert overall["take_calls"] == 4
    assert overall["shadow_calls"] == 1
    assert overall["right"] == 3  # WIN1, WIN2, SHAD
    assert overall["wrong"] == 1
    assert overall["neutral"] == 1
    assert overall["hit_rate_pct"] == 60.0
    assert overall["best_call"]["ticker"] == "WIN1"
    assert overall["worst_call"]["ticker"] == "LOSE"


def test_portfolio_pnl_is_equal_weight_over_take_calls(tmp_db, config):
    _seed(tmp_db, config)
    stats = compute_stats(tmp_db, config)
    # +40, +10, -85, -5 over the four TAKE calls
    assert stats["portfolio"]["equal_weight_pnl_pct_take_only"] == pytest.approx(-10.0, abs=0.01)
    assert stats["portfolio"]["take_calls_counted"] == 4


def test_breakdowns_cover_direction_asset_and_variant(tmp_db, config):
    _seed(tmp_db, config)
    stats = compute_stats(tmp_db, config)
    assert set(stats["by_direction"]) == {"long", "short"}
    assert set(stats["by_asset_type"]) == {"stock", "etf"}
    assert set(stats["by_variant"]) == {"squeeze", "momentum_breakout", "etf_momentum"}
    assert stats["by_asset_type"]["etf"]["total"] == 1
    assert stats["by_variant"]["squeeze"]["total"] == 2


def test_take_vs_skip_measures_the_judge(tmp_db, config):
    _seed(tmp_db, config)
    stats = compute_stats(tmp_db, config)
    block = stats["take_vs_skip"]
    assert block["take"]["total"] == 4
    assert block["skip_shadow"]["total"] == 1
    # TAKE averages -10%, the single shadow +20% -> the Judge is not adding value.
    assert block["judge_edge_avg_pnl_pct"] == pytest.approx(-30.0, abs=0.01)
    assert block["verdict"] == "Judge is not adding value"


def test_role_accuracy_uses_the_right_polarity(tmp_db, config):
    _seed(tmp_db, config)
    roles = compute_stats(tmp_db, config)["role_accuracy"]
    assert roles["researcher"]["avg_score_winners"] > roles["researcher"]["avg_score_others"]
    assert "lower is better" in roles["skeptic"]["polarity"]
    assert roles["skeptic"]["samples"] == 5


def test_confidence_buckets_follow_the_config(tmp_db, config):
    _seed(tmp_db, config)
    buckets = compute_stats(tmp_db, config)["confidence_buckets"]
    assert set(buckets) == {"0-40", "40-70", "70-100"}
    assert buckets["0-40"]["total"] == 1  # the shadow call at confidence 30
    assert buckets["70-100"]["total"] == 1  # WIN1 at 85


def test_renderers_produce_the_required_sections(tmp_db, config):
    _seed(tmp_db, config)
    stats = compute_stats(tmp_db, config)
    markdown = render_markdown(stats)
    for heading in (
        "## Overall",
        "### By direction",
        "### By asset type",
        "### By screen variant",
        "### TAKE vs SKIP",
        "### Per-role accuracy",
        "### Confidence buckets",
    ):
        assert heading in markdown
    assert "Judge edge" in markdown
    text = render_text(stats)
    assert "hit_rate" in text and "role skeptic" in text


# --------------------------------------------------------------- learning loop


def test_learning_loop_stays_quiet_below_min_samples(tmp_db, config):
    _seed(tmp_db, config)
    analysis = analyse(tmp_db, config)
    assert analysis["resolved_in_window"] == 5
    # min_samples is 10, so no role or judge proposal may be raised yet.
    assert not [
        proposal for proposal in analysis["proposals"] if proposal["lever"] == "role prompt"
    ]


def test_learning_loop_flags_a_losing_variant(tmp_db, config):
    config["learning"]["min_samples"] = 4
    for index in range(6):
        call_id = tmp_db.insert_call(
            review_payload(f"BAD{index}", entry=10.0, variant="squeeze"), run_id="r1"
        )
        tmp_db.apply_price(call_id, 7.0, close_threshold_pct=-80.0)
    analysis = analyse(tmp_db, config)
    variant_proposals = [
        proposal for proposal in analysis["proposals"] if proposal["lever"] == "screener filters"
    ]
    assert variant_proposals
    assert "squeeze" in variant_proposals[0]["target"]
    assert variant_proposals[0]["severity"] == "high"


def test_learning_loop_flags_a_judge_that_subtracts_value(tmp_db, config):
    config["learning"]["min_samples"] = 4
    for index in range(5):  # TAKE calls that lose
        call_id = tmp_db.insert_call(review_payload(f"T{index}", entry=10.0), run_id="r1")
        tmp_db.apply_price(call_id, 8.0, close_threshold_pct=-80.0)
    for index in range(3):  # shadow calls that win
        call_id = tmp_db.insert_call(
            review_payload(f"S{index}", decision="SKIP", entry=10.0), run_id="r1"
        )
        tmp_db.apply_price(call_id, 13.0, close_threshold_pct=-80.0)
    analysis = analyse(tmp_db, config)
    assert [
        proposal for proposal in analysis["proposals"] if proposal["lever"] == "judge weighting"
    ]


def test_learning_loop_proposes_nothing_automatically(tmp_db, config):
    config["learning"]["min_samples"] = 4
    for index in range(6):
        call_id = tmp_db.insert_call(
            review_payload(f"BAD{index}", entry=10.0, variant="squeeze"), run_id="r1"
        )
        tmp_db.apply_price(call_id, 7.0, close_threshold_pct=-80.0)
    markdown = render_improvements(analyse(tmp_db, config))
    assert "Nothing here is applied automatically" in markdown
    assert "**Approve?**" in markdown
    # The config on disk is untouched by the loop.
    assert config["screener"]["variants"]["squeeze"]["filters"][0] == "cap_smallunder"


def test_is_due_is_true_without_a_previous_file(config, tmp_path):
    config["tracker"]["improvements_file"] = str(tmp_path / "improvements.md")
    assert is_due(config) is True


def test_is_due_is_false_for_a_fresh_file(config, tmp_path):
    path = tmp_path / "improvements.md"
    path.write_text("# fresh", encoding="utf-8")
    config["tracker"]["improvements_file"] = str(path)
    assert is_due(config) is False


# ------------------------------------------------------------------ run cycle


def _cycle_kwargs(tmp_path, **overrides):
    kwargs = {
        "backend": "heuristic",
        "fixture": str(FIXTURE_HITS),
        "prices": {},
        "offline": True,
        "db_path": str(tmp_path / "cycle.db"),
    }
    kwargs.update(overrides)
    return kwargs


def test_cycle_screens_reviews_and_saves(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        now=datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc),
        **_cycle_kwargs(tmp_path),
    )
    assert report["screening_ran"] is True
    assert len(report["new_calls"]) == 3
    decisions = {call["ticker"]: call["decision"] for call in report["new_calls"]}
    assert decisions["PMPX"] == "SKIP"
    assert (tmp_path / "stats.md").is_file()
    assert "Lowcap Call Tracker" in (tmp_path / "stats.md").read_text(encoding="utf-8")


def test_cycle_skips_screening_on_a_weekend_but_still_prices(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    kwargs = _cycle_kwargs(tmp_path)
    first = run_cycle(config, now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc), **kwargs)
    assert first["screening_ran"] is True

    saturday = run_cycle(
        config,
        now=datetime(2026, 9, 19, 15, 0, tzinfo=timezone.utc),
        **_cycle_kwargs(tmp_path, prices={"SQZX": 4.5, "URAX": 19.0, "PMPX": 1.0}),
    )
    assert saturday["screening_ran"] is False
    assert "weekend" in saturday["session"]["reason"]
    assert saturday["new_calls"] == []
    assert saturday["price_update"]["priced"] == 3


def test_cycle_does_not_duplicate_an_open_ticker(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    kwargs = _cycle_kwargs(tmp_path)
    run_cycle(config, now=datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc), **kwargs)
    second = run_cycle(config, now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc), **kwargs)
    assert second["new_calls"] == []
    assert set(second["duplicates_skipped"]) == {"SQZX", "PMPX", "URAX"}


def test_cycle_honours_max_new_calls_per_run(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    config["tracker"]["max_new_calls_per_run"] = 1
    report = run_cycle(
        config,
        now=datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc),
        **_cycle_kwargs(tmp_path),
    )
    assert len(report["new_calls"]) == 1


def test_dry_run_writes_nothing(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        now=datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc),
        dry_run=True,
        **_cycle_kwargs(tmp_path),
    )
    assert len(report["new_calls"]) == 3
    assert all(call["call_id"] is None for call in report["new_calls"])
    assert not (tmp_path / "stats.md").exists()
    from call_db import CallDatabase

    with CallDatabase(tmp_path / "cycle.db") as db:
        assert db.all_calls() == []


def test_cycle_closes_a_call_that_breaches_the_threshold(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    kwargs = _cycle_kwargs(tmp_path)
    run_cycle(config, now=datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc), **kwargs)
    report = run_cycle(
        config,
        now=datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc),
        **_cycle_kwargs(tmp_path, prices={"SQZX": 0.4, "URAX": 19.0, "PMPX": 1.0}),
    )
    assert report["price_update"]["closed"] == 1
    closed = [update for update in report["price_update"]["updates"] if update["closed"]]
    assert closed[0]["ticker"] == "SQZX"


def test_run_row_is_recorded(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        now=datetime(2026, 9, 18, 11, 0, tzinfo=timezone.utc),
        **_cycle_kwargs(tmp_path),
    )
    from call_db import CallDatabase

    with CallDatabase(tmp_path / "cycle.db") as db:
        runs = db.runs()
        assert runs and runs[0]["run_id"] == report["run_id"]
        assert runs[0]["new_calls"] == 3
        assert runs[0]["new_takes"] == 2
        assert runs[0]["new_shadows"] == 1
        assert runs[0]["finished_at"] is not None


def test_price_fetch_without_yfinance_returns_nothing_rather_than_raising(monkeypatch):
    """yfinance absence degrades to 'no prices', which the update reports."""
    import price_update

    monkeypatch.setattr(price_update, "HAS_YFINANCE", False)
    assert price_update.fetch_prices(["AAA", "BBB"]) == {}


def test_update_reports_missing_prices_when_yfinance_is_absent(tmp_db, config, monkeypatch):
    import price_update

    monkeypatch.setattr(price_update, "HAS_YFINANCE", False)
    tmp_db.insert_call(review_payload("AAA", entry=10.0), run_id="r1")
    result = price_update.update_open_calls(tmp_db, config)
    assert result["priced"] == 0
    assert result["missing_prices"] == ["AAA"]
