"""JSON state snapshots: the continuity mechanism for throwaway working copies."""

import json
from datetime import datetime, timezone

import pytest
from call_db import STATUS_CLOSED_WRONG, STATUS_OPEN, CallDatabase
from run_cycle import run_cycle
from state_snapshot import (
    SNAPSHOT_VERSION,
    TABLES,
    SnapshotError,
    describe,
    export_snapshot,
    import_snapshot,
    load_snapshot,
    snapshot_path,
)

from conftest import FIXTURE_HITS, review_payload


def _seed(db, config):
    open_call = db.insert_call(review_payload("OPEN1", entry=10.0), run_id="r1")
    db.apply_price(open_call, 12.0, close_threshold_pct=-80.0)
    shadow = db.insert_call(review_payload("SHDW1", decision="SKIP", entry=5.0), run_id="r1")
    db.apply_price(shadow, 6.0, close_threshold_pct=-80.0)
    closed = db.insert_call(review_payload("DEAD1", entry=10.0), run_id="r1")
    db.apply_price(closed, 1.0, close_threshold_pct=-80.0)
    db.start_run("r1", session_reason="test", screening_ran=True)
    db.record_llm_usage(
        {
            "run_id": "r1",
            "month": "2026-09",
            "role": "judge",
            "model": "claude-sonnet-5",
            "input_tokens": 100,
            "output_tokens": 50,
            "cost_usd": 0.001,
        }
    )
    return open_call, shadow, closed


def test_export_covers_every_table(tmp_db, config, tmp_path):
    _seed(tmp_db, config)
    snapshot = export_snapshot(tmp_db, tmp_path / "snap.json")
    assert set(snapshot["tables"]) == set(TABLES)
    assert snapshot["snapshot_version"] == SNAPSHOT_VERSION
    assert snapshot["counts"]["calls"] == 3
    assert snapshot["counts"]["role_verdicts"] == 15  # five roles per call
    assert snapshot["counts"]["llm_usage"] == 1
    assert (tmp_path / "snap.json").is_file()


def test_round_trip_preserves_calls_verdicts_and_prices(tmp_db, config, tmp_path):
    _seed(tmp_db, config)
    before = {row["ticker"]: dict(row) for row in tmp_db.all_calls()}
    verdicts_before = tmp_db.verdicts_for(tmp_db.open_call_for("OPEN1")["id"])
    export_snapshot(tmp_db, tmp_path / "snap.json")

    with CallDatabase(tmp_path / "restored.db") as restored:
        result = import_snapshot(restored, tmp_path / "snap.json")
        assert result["imported"] is True
        after = {row["ticker"]: dict(row) for row in restored.all_calls()}
        assert after == before  # every column, including ids and timestamps
        assert restored.verdicts_for(restored.open_call_for("OPEN1")["id"]) == verdicts_before
        assert restored.call(3)["status"] == STATUS_CLOSED_WRONG
        prices = list(restored.conn.execute("SELECT * FROM price_history"))
        assert len(prices) == 6  # entry + update for each of the three calls


def test_import_refuses_to_clobber_live_state(tmp_db, config, tmp_path):
    _seed(tmp_db, config)
    export_snapshot(tmp_db, tmp_path / "snap.json")
    result = import_snapshot(tmp_db, tmp_path / "snap.json")
    assert result["imported"] is False
    assert "already holds" in result["reason"]
    assert len(tmp_db.all_calls()) == 3  # untouched


def test_replace_overwrites_deliberately(tmp_db, config, tmp_path):
    _seed(tmp_db, config)
    export_snapshot(tmp_db, tmp_path / "snap.json")
    tmp_db.insert_call(review_payload("EXTRA", entry=4.0), run_id="r2")
    assert len(tmp_db.all_calls()) == 4
    result = import_snapshot(tmp_db, tmp_path / "snap.json", replace=True)
    assert result["imported"] is True
    assert {row["ticker"] for row in tmp_db.all_calls()} == {"OPEN1", "SHDW1", "DEAD1"}


def test_dedupe_survives_a_restore(tmp_db, config, tmp_path):
    """The point of the snapshot: a fresh checkout must not re-open a live call."""
    _seed(tmp_db, config)
    export_snapshot(tmp_db, tmp_path / "snap.json")
    with CallDatabase(tmp_path / "restored.db") as restored:
        import_snapshot(restored, tmp_path / "snap.json")
        assert restored.open_call_for("OPEN1") is not None
        assert restored.insert_call(review_payload("OPEN1", entry=10.0), run_id="r9") is None
        # A call closed before the snapshot is callable again, as it should be.
        assert restored.insert_call(review_payload("DEAD1", entry=2.0), run_id="r9") is not None


def test_pnl_continues_from_the_original_entry(tmp_db, config, tmp_path):
    _seed(tmp_db, config)
    export_snapshot(tmp_db, tmp_path / "snap.json")
    with CallDatabase(tmp_path / "restored.db") as restored:
        import_snapshot(restored, tmp_path / "snap.json")
        call_id = restored.open_call_for("OPEN1")["id"]
        result = restored.apply_price(call_id, 20.0, close_threshold_pct=-80.0)
        assert result["pnl_pct"] == pytest.approx(100.0)  # entry 10.0 was preserved


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ("{not json", "not valid JSON"),
        (json.dumps({"nope": 1}), "no 'tables'"),
        (json.dumps({"snapshot_version": 99, "tables": {}}), "not supported"),
    ],
)
def test_corrupt_snapshots_are_rejected(tmp_path, payload, match):
    path = tmp_path / "bad.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(SnapshotError, match=match):
        load_snapshot(path)


def test_missing_snapshot_is_reported(tmp_path):
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot(tmp_path / "nope.json")


def test_snapshot_is_disabled_unless_configured(config):
    assert snapshot_path(config) is None
    config["tracker"]["snapshot_file"] = "tracker-output/state_snapshot.json"
    assert snapshot_path(config).name == "state_snapshot.json"
    assert snapshot_path(config, "/tmp/other.json").name == "other.json"  # noqa: S108


def test_describe_summarizes_for_a_human(tmp_db, config, tmp_path):
    _seed(tmp_db, config)
    text = describe(export_snapshot(tmp_db, tmp_path / "snap.json"))
    assert "calls=3" in text
    assert "OPEN1" in text
    assert "DEAD1" not in text  # closed calls are not "open"


# ------------------------------------------------------- cycle integration


def test_cycle_restores_and_rewrites_the_snapshot(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    snapshot = tmp_path / "snap.json"
    common = dict(
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        telegram=False,
        snapshot=str(snapshot),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )

    first = run_cycle(config, db_path=str(tmp_path / "run1.db"), **common)
    assert len(first["new_calls"]) == 3
    assert snapshot.is_file()

    # A brand-new working copy: different database file, same snapshot.
    second = run_cycle(config, db_path=str(tmp_path / "run2.db"), **common)
    assert second["snapshot_import"]["imported"] is True
    assert second["snapshot_import"]["counts"]["calls"] == 3
    assert second["new_calls"] == []  # dedupe survived the fresh checkout
    assert set(second["duplicates_skipped"]) == {"SQZX", "PMPX", "URAX"}
    assert second["stats"]["overall"]["total"] == 3  # history intact, not doubled


def test_cycle_without_a_snapshot_path_writes_none(config, tmp_path):
    config["tracker"]["stats_file"] = str(tmp_path / "stats.md")
    report = run_cycle(
        config,
        backend="heuristic",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        telegram=False,
        db_path=str(tmp_path / "run.db"),
        now=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert "snapshot_file" not in report
    assert not list(tmp_path.glob("*.json"))


def test_snapshot_json_is_diff_friendly(tmp_db, config, tmp_path):
    """Git-friendliness is the point: stable key order, one row per block."""
    _seed(tmp_db, config)
    path = tmp_path / "snap.json"
    export_snapshot(tmp_db, path)
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    first = json.loads(text)
    export_snapshot(tmp_db, path)
    second = json.loads(path.read_text(encoding="utf-8"))
    first.pop("exported_at"), second.pop("exported_at")
    assert first == second  # only the timestamp moves between exports


def test_open_calls_survive_a_move_to_another_host(tmp_db, config, tmp_path):
    """Migration path: export here, import on the VPS, keep every open call."""
    _seed(tmp_db, config)
    export_snapshot(tmp_db, tmp_path / "snap.json")
    with CallDatabase(tmp_path / "vps.db") as vps:
        import_snapshot(vps, tmp_path / "snap.json")
        open_tickers = {row["ticker"] for row in vps.open_calls()}
        assert open_tickers == {"OPEN1", "SHDW1"}
        assert all(row["status"] == STATUS_OPEN for row in vps.open_calls())
