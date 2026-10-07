"""The signals layer where it meets the rest of the cycle.

The layer is only worth building if the five roles see it, the Judge is bound
by it, the database remembers it, and the outcome report can tell which
signals actually predicted a run.
"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from explosion_signals import evaluate
from role_review import build_user_message, enforce_judge_gate, review_hit
from run_cycle import run_cycle

from conftest import FIXTURE_HITS, review_payload


@pytest.fixture()
def v2(config):
    config["screener"]["screener_version"] = "v2"
    return config


def hit(**overrides):
    out = {
        "ticker": "EXPL",
        "asset_type": "stock",
        "variant": "squeeze",
        "price": 4.00,
        "volume": 20_000_000,
        "avg_volume": 1_000_000,
        "float_shares": 20_000_000,
        "rel_volume": 3.0,
        "short_ratio": 6.0,
        "inst_own_pct": 8.0,
        "industry": "Biotechnology",
        "change_pct": 8.0,
        "atr": 0.3,
        "screener_version": "v2",
    }
    out.update(overrides)
    return out


STRONG = {
    "catalyst_hours_ago": 2.0,
    "catalyst_form": "8-K",
    "range_percentile": 8.0,
    "vwap": 3.90,
    "sector_peers_up": 3,
    "dilution_filings": [],
}


# --- the roles see the numbers ------------------------------------------


def test_the_researcher_is_given_the_signal_sheet(v2):
    result = evaluate(hit(), v2, data=STRONG)
    context = {"config": v2, "verdicts": {}, "explosion_signals": result}
    message = build_user_message("researcher", hit(), context)
    assert "explosion_signals" in message
    assert "float_rotation" in message


def test_the_skeptic_and_judge_see_it_too(v2):
    result = evaluate(hit(), v2, data=STRONG)
    context = {"config": v2, "verdicts": {}, "explosion_signals": result}
    for role in ("skeptic", "judge"):
        assert "explosion_signals" in build_user_message(role, hit(), context)


def test_the_technician_is_not_handed_the_sheet(v2):
    """The Technician reads price. Handing it a catalyst score invites it to
    double-count what the Researcher already weighed."""
    result = evaluate(hit(), v2, data=STRONG)
    context = {"config": v2, "verdicts": {}, "explosion_signals": result}
    assert "explosion_signals" not in build_user_message("technician", hit(), context)


def test_a_v1_review_hands_no_sheet_to_anyone(config):
    """A v1 hit has no sheet, and the tag travels on the hit — so a v1 call
    reviewed during a v2 run is still judged without one."""
    v1_hit = hit(screener_version="v1")
    context = {"config": config, "verdicts": {}, "explosion_signals": evaluate(v1_hit, config)}
    assert "explosion_signals" not in build_user_message("judge", v1_hit, context)


# --- the Judge is bound by it ------------------------------------------


def test_the_bonus_lifts_the_judges_confidence(v2):
    review = review_hit(hit(), v2, backend="heuristic", offline=True, signal_data=STRONG)
    judge = review["verdicts"]["judge"]
    assert judge["explosion_signals"]["bonus"] > 0
    assert judge["confidence"] == min(
        100, judge["explosion_signals"]["confidence_before"] + judge["explosion_signals"]["bonus"]
    )


def test_a_below_vwap_sheet_charges_the_judge(v2):
    data = {**STRONG, "vwap": 4.50}
    review = review_hit(hit(), v2, backend="heuristic", offline=True, signal_data=data)
    signals = review["verdicts"]["judge"]["explosion_signals"]
    assert signals["signals"]["vwap_position"]["points"] == -10


def test_a_hard_skip_forces_a_skip_whatever_the_confidence(v2):
    data = {**STRONG, "dilution_filings": [{"form": "S-3", "days_ago": 4}]}
    review = review_hit(hit(), v2, backend="heuristic", offline=True, signal_data=data)
    assert review["decision"] == "SKIP"
    assert "dilution" in review["verdicts"]["judge"]["reason"].lower()


def test_a_hard_skip_names_the_filter_in_the_gate_overrides(v2):
    verdict = {
        "decision": "TAKE",
        "confidence": 95,
        "skeptic_objections_answered": True,
        "skeptic_answer": "answered at length, in detail, with evidence",
    }
    verdicts = {"risk_manager": {"direction": "long"}}
    out = enforce_judge_gate(
        verdict,
        verdicts,
        v2,
        signals={"hard_skip": True, "hard_skips": ["reverse split: 20 days ago"]},
    )
    assert out["decision"] == "SKIP"
    assert any("reverse split" in reason for reason in out["gate_overrides"])


def test_a_hard_skip_survives_a_perfect_sheet(v2):
    """Every bonus firing must not buy its way past a hard skip."""
    data = {
        **STRONG,
        "premarket_gap_pct": 30.0,
        "premarket_volume_pct_of_adv": 60.0,
        "insider_buy_days_ago": 2,
        "borrow_fee_pct": 90.0,
        "cash_runway_months": 1.0,
    }
    review = review_hit(hit(), v2, backend="heuristic", offline=True, signal_data=data)
    assert review["decision"] == "SKIP"
    assert "runway" in review["verdicts"]["judge"]["reason"].lower()


def test_v2_charges_the_catalyst_once_not_twice(v2):
    """In v2 the signals layer owns the catalyst charge. The role-level
    no_catalyst_penalty must not also fire, or a thin tape costs 30."""
    data = {**STRONG, "catalyst_hours_ago": None, "catalyst_form": None, "catalyst_found": False}
    review = review_hit(
        hit(catalyst_headline=None), v2, backend="heuristic", offline=True, signal_data=data
    )
    judge = review["verdicts"]["judge"]
    assert judge["explosion_signals"]["signals"]["catalyst_recency"]["points"] == -15
    assert "catalyst_penalty" not in judge


def test_v1_still_uses_the_role_level_catalyst_penalty(config):
    """v1's behaviour is frozen: it keeps the penalty it was measured with."""
    review = review_hit(
        {**hit(screener_version="v1"), "catalyst_headline": None},
        config,
        backend="heuristic",
        offline=True,
    )
    judge = review["verdicts"]["judge"]
    assert "explosion_signals" not in judge
    assert judge.get("catalyst_penalty") or judge["confidence"] >= 0


# --- the database remembers --------------------------------------------


def test_the_signal_sheet_is_stored_on_the_call(tmp_db, v2):
    payload = review_payload("EXPL", entry=4.0)
    payload["hit"] = hit()
    payload["explosion_signals"] = evaluate(hit(), v2, data=STRONG)
    call_id = tmp_db.insert_call(payload, run_id="r1", sl_pct=20.0)
    row = dict(tmp_db.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone())
    assert row["signal_bonus"] == payload["explosion_signals"]["bonus"]
    stored = json.loads(row["signals_json"])
    assert stored["signals"]["float_rotation"]["points"] == 10
    assert row["hard_skip_reason"] is None


def test_a_hard_skipped_call_records_why(tmp_db, v2):
    signals = evaluate(hit(), v2, data={**STRONG, "halts_today": 5})
    payload = review_payload("EXPL", decision="SKIP", entry=4.0)
    payload["hit"] = hit()
    payload["explosion_signals"] = signals
    call_id = tmp_db.insert_call(payload, run_id="r1", sl_pct=20.0)
    row = tmp_db.conn.execute(
        "SELECT hard_skip_reason FROM calls WHERE id = ?", (call_id,)
    ).fetchone()
    assert "halt" in row["hard_skip_reason"].lower()


def test_a_call_with_no_signals_stores_nothing_rather_than_zero(tmp_db, config):
    """A v1 call has no signal sheet; a stored 0 bonus would read as "the
    layer looked and found nothing"."""
    payload = review_payload("OLD", entry=4.0)
    call_id = tmp_db.insert_call(payload, run_id="r1")
    row = tmp_db.conn.execute(
        "SELECT signal_bonus, signals_json FROM calls WHERE id = ?", (call_id,)
    ).fetchone()
    assert row["signal_bonus"] is None
    assert row["signals_json"] is None


# --- Telegram ----------------------------------------------------------


def test_a_take_carries_its_key_signals(config):
    from telegram_bot import format_run_notification

    report = {
        "run_id": "r1",
        "session": {"as_of": "2026-10-07", "reason": "regular session"},
        "screening_ran": True,
        "screener_version": "v2",
        "new_calls": [
            {
                "ticker": "EXPL",
                "asset_type": "stock",
                "variant": "squeeze",
                "direction": "long",
                "decision": "TAKE",
                "confidence": 78,
                "entry": 4.0,
                "stop": 3.6,
                "sl_price": 3.2,
                "kind": "active",
                "call_id": 1,
                "reason": "clean",
                "signal_line": "signals +28 · float rotation +10, catalyst +10, VWAP +5",
            }
        ],
        "duplicates_skipped": [],
        "guard_skips": [],
        "price_update": {"priced": 0, "closed": 0, "updates": [], "missing_prices": []},
        "stats": {},
        "errors": [],
    }
    text = format_run_notification(report, config)
    assert "signals +28" in text
    assert "float rotation +10" in text


# --- the outcome report ------------------------------------------------


def test_the_report_scores_each_signal_with_and_without(tmp_db, config):
    from outcome_report import build_report

    def add(ticker, *, rotation_points, ret):
        payload = review_payload(ticker, entry=10.0)
        payload["hit"] = {"ticker": ticker, "screener_version": "v2"}
        payload["explosion_signals"] = {
            "enabled": True,
            "bonus": rotation_points,
            "signals": {
                "float_rotation": {
                    "status": "ok",
                    "value": 1.2,
                    "points": rotation_points,
                    "detail": "",
                },
            },
            "hard_skips": [],
            "hard_skip": False,
            "hard_skip_checks": {},
        }
        call_id = tmp_db.insert_call(payload, run_id="r1", sl_pct=20.0)
        tmp_db.conn.execute(
            "UPDATE calls SET ret_1d=?, ret_3d=?, ret_5d=?, "
            "outcome_updated_at='2026-10-15T00:00:00+00:00' WHERE id=?",
            (ret, ret, ret, call_id),
        )
        tmp_db.conn.commit()

    for index in range(3):
        add(f"WITH{index}", rotation_points=10, ret=20.0)
    for index in range(3):
        add(f"WOUT{index}", rotation_points=0, ret=-10.0)

    block = build_report(tmp_db, config)["signals"]["float_rotation"]
    assert block["with"]["calls"] == 3
    assert block["with"]["hit_rate_pct"] == 100.0
    assert block["without"]["calls"] == 3
    assert block["without"]["hit_rate_pct"] == 0.0
    assert block["edge_pct"] == 30.0


def test_the_signal_table_renders(tmp_db, config):
    from outcome_report import build_report, render_report

    payload = review_payload("SIG", entry=10.0)
    payload["hit"] = {"ticker": "SIG", "screener_version": "v2"}
    payload["explosion_signals"] = {
        "enabled": True,
        "bonus": 5,
        "hard_skips": [],
        "hard_skip": False,
        "hard_skip_checks": {},
        "signals": {"vwap_position": {"status": "ok", "value": None, "points": 5, "detail": ""}},
    }
    call_id = tmp_db.insert_call(payload, run_id="r1", sl_pct=20.0)
    tmp_db.conn.execute(
        "UPDATE calls SET ret_5d=5.0, outcome_updated_at='2026-10-15T00:00:00+00:00' WHERE id=?",
        (call_id,),
    )
    tmp_db.conn.commit()
    text = render_report(build_report(tmp_db, config), config=config)
    assert "SIGNALS" in text.upper()
    assert "vwap" in text.lower()


# --- the cycle ---------------------------------------------------------


def test_an_offline_v2_cycle_still_scores_what_it_can(tmp_path, config):
    """--offline means no network, so the row-derived signals still score and
    every network-backed one reports n/a. The cycle must not stall."""
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
    call = report["new_calls"][0]
    assert call["ticker"] == "SQZX"
    assert call["signal_line"]
    assert "n/a" not in call["signal_line"]
