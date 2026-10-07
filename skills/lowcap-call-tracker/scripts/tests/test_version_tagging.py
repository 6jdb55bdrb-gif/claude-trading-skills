"""Every logged call records the screener generation and the stop it was taken with.

The whole point of running two generations side by side is being able to ask,
later, which one produced the winners. That is only answerable if the version
and the stop are written onto the call at insert time, where they are facts,
rather than re-derived from whatever the config says the day the report runs.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from run_cycle import run_cycle

from conftest import FIXTURE_HITS, review_payload


def _row(db, call_id):
    cursor = db.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
    return dict(cursor.fetchone())


def test_the_version_is_taken_from_the_hit_when_the_caller_says_nothing(tmp_db):
    """The screener tags the row; the database should not have to be told twice."""
    payload = review_payload("TAG", entry=10.0)
    payload["hit"] = {"ticker": "TAG", "screener_version": "v2", "atr": 0.5}
    call_id = tmp_db.insert_call(payload, run_id="r1")
    assert _row(tmp_db, call_id)["screener_version"] == "v2"


def test_an_explicit_version_wins_over_the_hit(tmp_db):
    payload = review_payload("TAG2", entry=10.0)
    payload["hit"] = {"ticker": "TAG2", "screener_version": "v2"}
    call_id = tmp_db.insert_call(payload, run_id="r1", screener_version="v1")
    assert _row(tmp_db, call_id)["screener_version"] == "v1"


def test_a_call_from_a_pre_version_hit_records_no_version(tmp_db):
    """An older row carries no tag, and nothing is invented for it."""
    call_id = tmp_db.insert_call(review_payload("OLD", entry=10.0), run_id="r1")
    assert _row(tmp_db, call_id)["screener_version"] is None


def test_the_stop_is_computed_against_the_stored_entry(tmp_db):
    call_id = tmp_db.insert_call(review_payload("SL", entry=4.57), run_id="r1", sl_pct=20.0)
    row = _row(tmp_db, call_id)
    assert row["entry_price"] == 4.57
    assert row["sl_price"] == 3.66


def test_no_stop_percentage_means_no_stored_stop(tmp_db):
    """`sl_pct: null` disables the fixed stop rather than defaulting to one."""
    call_id = tmp_db.insert_call(review_payload("NOSL", entry=10.0), run_id="r1")
    assert _row(tmp_db, call_id)["sl_price"] is None


def test_a_skip_gets_a_stop_too(tmp_db):
    """A SKIP is tracked as a shadow call, so it needs the same stop to be
    comparable with the TAKEs in the outcome report."""
    call_id = tmp_db.insert_call(
        review_payload("SHAD", decision="SKIP", entry=10.0), run_id="r1", sl_pct=20.0
    )
    assert _row(tmp_db, call_id)["sl_price"] == 8.0


def test_a_cycle_tags_its_calls_with_the_version_it_ran(tmp_path, config):
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        force_screen=True,
        offline=True,
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert report["screener_version"] == "v2"
    from call_db import CallDatabase

    with CallDatabase(tmp_path / "calls.db") as db:
        rows = db.conn.execute("SELECT ticker, screener_version, sl_price, entry_price FROM calls")
        tagged = {row["ticker"]: dict(row) for row in rows}
    assert tagged, "the cycle recorded no calls"
    assert {row["screener_version"] for row in tagged.values()} == {"v2"}
    for row in tagged.values():
        assert row["sl_price"] == round(row["entry_price"] * 0.8, 2)
    # v2 has no ETF variant and refuses to chase PMPX's +41% day.
    assert set(tagged) == {"SQZX"}


def test_a_v1_cycle_is_unchanged_by_any_of_this(tmp_path, config):
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        force_screen=True,
        offline=True,
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert report["screener_version"] == "v1"
    assert {call["ticker"] for call in report["new_calls"]} == {"SQZX", "PMPX", "URAX"}


def test_an_early_v2_run_logs_a_skip_instead_of_screening(tmp_path, config):
    """Before 16:30 Zurich a v2 run still prices the open book — it just does
    not screen, because relative volume means nothing yet."""
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        force_screen=True,
        offline=True,
        now=datetime(2026, 10, 7, 15, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert report["screening_ran"] is False
    assert "16:30" in report["screen_skipped"]
    assert report["hits"] == 0
    assert report["new_calls"] == []


def test_a_late_v2_run_screens(tmp_path, config):
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        force_screen=True,
        offline=True,
        now=datetime(2026, 10, 7, 17, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert report["screening_ran"] is True
    assert "screen_skipped" not in report


def test_an_early_v1_run_still_screens(tmp_path, config):
    """The gate belongs to v2 only: v1 keeps the behaviour it was measured with."""
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        force_screen=True,
        offline=True,
        now=datetime(2026, 10, 7, 9, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert report["screening_ran"] is True


def test_the_capped_name_is_reported_not_silently_dropped(tmp_path, config):
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        screener_version="v2",
        force_screen=True,
        offline=True,
        now=datetime(2026, 10, 7, 17, 0, tzinfo=ZoneInfo("Europe/Zurich")),
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert [skip["ticker"] for skip in report["guard_skips"]] == ["PMPX"]


def test_a_cycle_measures_outcomes_and_carries_the_scorecard(tmp_path, config):
    """The scorecard has to be produced by the run that sends the message, or
    it will only ever be looked at when someone remembers to ask for it."""
    from call_db import CallDatabase

    db_path = tmp_path / "calls.db"
    run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        force_screen=True,
        offline=True,
        db_path=str(db_path),
        telegram=False,
        prices={},
    )
    # Age the book so there are sessions to measure: a call made today has none.
    with CallDatabase(db_path) as db:
        db.conn.execute("UPDATE calls SET call_date = '2026-09-28T20:00:00+00:00'")
        db.conn.commit()
        tickers = [row["ticker"] for row in db.conn.execute("SELECT ticker FROM calls")]
    history = {
        ticker: [
            {"date": "2026-09-29", "low": 9.9, "close": 10.0},
            {"date": "2026-09-30", "low": 9.9, "close": 10.0},
            {"date": "2026-10-01", "low": 9.9, "close": 10.0},
        ]
        for ticker in tickers
    }

    report = run_cycle(
        config,
        backend="heuristic",
        # The same fixture again: every name is already open, so nothing new is
        # logged and no request leaves the machine.
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        db_path=str(db_path),
        telegram=False,
        prices={},
        bars=history,
    )
    assert report["outcomes"]["updated"] == len(tickers)
    assert report["scorecard_report"]["total_calls"] == len(tickers)
    # Three calls is far short of 30, so nothing goes to Telegram yet.
    assert report.get("scorecard") is None


def test_an_offline_run_does_not_pretend_to_measure_anything(tmp_path, config):
    """No network means the measurement waits, rather than a data gap being
    written down as a result."""
    report = run_cycle(
        config,
        backend="heuristic",
        screen_mode="fixture",
        fixture=str(FIXTURE_HITS),
        force_screen=True,
        offline=True,
        db_path=str(tmp_path / "calls.db"),
        telegram=False,
        prices={},
    )
    assert "outcomes" not in report
