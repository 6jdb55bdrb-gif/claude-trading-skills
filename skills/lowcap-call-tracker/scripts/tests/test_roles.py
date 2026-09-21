"""Role scoring, the Judge gate, and the LLM backend contract."""

import json

import heuristic_roles as H
import pytest
from fetch_screener import load_fixture
from llm_client import LLMClient, LLMUnavailable, extract_json
from role_review import (
    ROLE_FILES,
    ReviewUnavailable,
    agents_dir,
    build_user_message,
    enforce_judge_gate,
    load_role_prompt,
    review_hit,
    review_hits,
)

from conftest import FIXTURE_HITS, FakeAnthropic

# ------------------------------------------------------------------ RESEARCHER


def test_no_catalyst_scores_low(stock_hit):
    del stock_hit["catalyst_headline"]
    verdict = H.researcher(stock_hit)
    assert verdict["catalyst_type"] == "none_found"
    assert verdict["score"] <= 3
    assert "no catalyst" in " ".join(verdict["reasons"]).lower()


def test_episodic_pivot_score_drives_the_catalyst_rating(stock_hit):
    verdict = H.researcher(
        stock_hit,
        episodic_pivot={
            "composite_score": 82.0,
            "catalyst_type": "fda_approval",
            "ep_type": "FDA_EP",
            "rating": "A",
        },
    )
    assert verdict["catalyst_type"] == "fda_regulatory"
    assert verdict["score"] >= 8
    assert "episodic-pivot analyzer" in verdict["reasons"][0]


def test_etf_catalyst_is_the_basket_theme(etf_hit):
    verdict = H.researcher(etf_hit)
    assert verdict["catalyst_type"] in {"sector_theme", "none_found"}
    assert any("etf" in reason.lower() for reason in verdict["reasons"])


# ------------------------------------------------------------------ TECHNICIAN


def test_extension_above_sma20_is_penalized(stock_hit):
    modest = H.technician({**stock_hit, "sma20_pct": 8.0})
    extended = H.technician({**stock_hit, "sma20_pct": 55.0})
    assert extended["score"] < modest["score"]
    assert extended["extension_pct_sma20"] == 55.0


def test_climactic_volume_is_penalized(stock_hit):
    confirming = H.technician({**stock_hit, "rel_volume": 3.0})
    climactic = H.technician({**stock_hit, "rel_volume": 12.0})
    assert climactic["volume_pattern"] == "climactic"
    assert confirming["volume_pattern"] == "confirming"
    assert climactic["score"] < confirming["score"]


def test_score_is_capped_without_price_history(stock_hit):
    assert H.technician(stock_hit)["score"] <= 6.0


def test_weekly_swing_levels_are_preferred_when_available(stock_hit):
    verdict = H.technician(
        stock_hit,
        weekly={
            "verdict": "CONTINUATION",
            "confidence": "HIGH",
            "swing_levels": {"support": 3.11, "resistance": 4.90},
        },
    )
    assert verdict["support"] == 3.11
    assert verdict["resistance"] == 4.90


def test_support_falls_back_to_the_sma20_level(stock_hit):
    verdict = H.technician(stock_hit)
    assert verdict["support"] == pytest.approx(stock_hit["price"] / 1.18, abs=0.01)


# --------------------------------------------------------------------- SKEPTIC


def test_skeptic_score_is_objection_severity(stock_hit):
    clean = H.skeptic(
        {**stock_hit, "sma20_pct": 6.0, "rel_volume": 2.2},
        researcher_verdict={"score": 8},
    )
    ugly = H.skeptic(
        {**stock_hit, "price": 0.9, "sma20_pct": 70.0, "rel_volume": 14.0, "avg_volume": 200_000},
        researcher_verdict={"score": 1},
    )
    assert ugly["score"] > clean["score"]
    assert ugly["score"] >= 8
    assert "severity" in ugly["score_polarity"]


def test_skeptic_flags_dilution_on_sub_dollar_prices(stock_hit):
    verdict = H.skeptic({**stock_hit, "price": 1.1}, researcher_verdict={"score": 7})
    assert any("offering" in flag or "ATM" in flag for flag in verdict["risk_flags"])


def test_skeptic_never_flags_float_for_etfs(etf_hit):
    verdict = H.skeptic(etf_hit, researcher_verdict={"score": 6})
    assert "float" not in " ".join(verdict["risk_flags"]).lower()


def test_skeptic_flags_leveraged_etf_decay():
    verdict = H.skeptic(
        {
            "ticker": "URAX",
            "company": "Ultra Uranium 3X Bull ETF",
            "asset_type": "etf",
            "price": 12.0,
            "avg_volume": 300_000,
        },
        researcher_verdict={"score": 6},
    )
    assert verdict["objection_category"] == "etf_mechanics"
    assert any("decay" in flag for flag in verdict["risk_flags"])


def test_skeptic_finds_no_objection_on_a_clean_setup():
    verdict = H.skeptic(
        {
            "ticker": "CLEAN",
            "asset_type": "stock",
            "price": 8.0,
            "avg_volume": 4_000_000,
            "rel_volume": 2.5,
            "sma20_pct": 7.0,
            "short_float_pct": 18.0,
        },
        researcher_verdict={"score": 8},
    )
    assert verdict["objection_category"] == "none"
    assert verdict["score"] <= 2


# ---------------------------------------------------------------- RISK MANAGER


def test_long_is_the_default_direction(stock_hit, config):
    tech = H.technician(stock_hit)
    verdict = H.risk_manager(
        stock_hit, technician_verdict=tech, skeptic_verdict={"score": 3}, config=config
    )
    assert verdict["direction"] == "long"
    assert verdict["stop"] < verdict["entry"]


def test_short_needs_extension_plus_a_severe_objection(stock_hit, config):
    hit = {**stock_hit, "sma20_pct": 70.0}
    tech = H.technician(hit)
    verdict = H.risk_manager(
        hit, technician_verdict=tech, skeptic_verdict={"score": 9}, config=config
    )
    assert verdict["direction"] == "short"
    assert verdict["stop"] > verdict["entry"]


def test_stop_distance_is_capped_at_20_percent(stock_hit, config):
    verdict = H.risk_manager(
        stock_hit,
        technician_verdict={"support": 0.5, "extension_pct_sma20": 10.0, "trend": "uptrend"},
        skeptic_verdict={"score": 3},
        config=config,
    )
    assert verdict["stop"] == pytest.approx(stock_hit["price"] * 0.8, abs=0.01)


def test_position_sizer_result_is_used_when_supplied(stock_hit, config):
    verdict = H.risk_manager(
        stock_hit,
        technician_verdict=H.technician(stock_hit),
        skeptic_verdict={"score": 3},
        config=config,
        sizing={"shares": 42, "position_usd": 159.6, "risk_usd": 100.0, "binding_constraint": None},
    )
    assert verdict["shares"] == 42
    assert "position-sizer" in " ".join(verdict["reasons"])


def test_missing_price_yields_no_plan(config):
    verdict = H.risk_manager({"ticker": "X", "asset_type": "stock"}, config=config)
    assert verdict["direction"] == "none"
    assert verdict["score"] == 0.0


# ----------------------------------------------------------------------- JUDGE


def _verdicts(researcher=8.0, technician=7.0, skeptic=2.0, risk=7.0, direction="long"):
    return {
        "researcher": {"score": researcher, "catalyst_type": "contract_award"},
        "technician": {"score": technician, "trend": "uptrend"},
        "skeptic": {
            "score": skeptic,
            "objection_category": "extension" if skeptic > 2 else "none",
            "strongest_objection": "extended entry",
        },
        "risk_manager": {
            "score": risk,
            "direction": direction,
            "stop": 3.2,
            "stop_basis": "structure",
        },
    }


def test_strong_setup_is_taken(config):
    verdict = H.judge(_verdicts(), config=config)
    assert verdict["decision"] == "TAKE"
    assert verdict["confidence"] >= config["roles"]["judge"]["min_confidence_to_take"]


def test_severe_dilution_objection_forces_a_skip(config):
    verdicts = _verdicts(skeptic=9.0)
    verdicts["skeptic"]["objection_category"] = "dilution"
    verdict = H.judge(verdicts, config=config)
    assert verdict["decision"] == "SKIP"
    assert verdict["skeptic_objections_answered"] is False


def test_no_direction_forces_a_skip(config):
    verdict = H.judge(_verdicts(direction="none"), config=config)
    assert verdict["decision"] == "SKIP"
    assert "no executable plan" in verdict["reason"]


def test_confidence_floor_is_applied(config):
    """Objection answered, plan exists — but the blend lands under the floor."""
    verdict = H.judge(
        _verdicts(researcher=6.0, technician=6.0, risk=6.0, skeptic=7.5), config=config
    )
    assert verdict["skeptic_objections_answered"] is True
    assert verdict["decision"] == "SKIP"
    assert "below the" in verdict["reason"]
    assert verdict["confidence"] < config["roles"]["judge"]["min_confidence_to_take"]


def test_confidence_is_monotonic_in_the_scores(config):
    weak = H.judge(_verdicts(researcher=4.0, technician=4.0), config=config)["confidence"]
    strong = H.judge(_verdicts(researcher=10.0, technician=10.0), config=config)["confidence"]
    assert strong > weak


def test_skeptic_penalty_lowers_confidence(config):
    low = H.judge(_verdicts(skeptic=1.0), config=config)["confidence"]
    high = H.judge(_verdicts(skeptic=9.0), config=config)["confidence"]
    assert high < low


# ------------------------------------------------------------- the code gate


def test_gate_overturns_a_take_with_an_unanswered_objection(config):
    judged = {
        "role": "judge",
        "decision": "TAKE",
        "confidence": 90,
        "reason": "looks good",
        "skeptic_objections_answered": False,
        "skeptic_answer": "",
    }
    result = enforce_judge_gate(judged, _verdicts(), config)
    assert result["decision"] == "SKIP"
    assert "not explicitly answered" in result["gate_overrides"][0]


def test_gate_rejects_a_token_answer(config):
    judged = {
        "decision": "TAKE",
        "confidence": 90,
        "skeptic_objections_answered": True,
        "skeptic_answer": "Noted.",
        "reason": "x",
    }
    assert enforce_judge_gate(judged, _verdicts(), config)["decision"] == "SKIP"


def test_gate_enforces_the_confidence_floor(config):
    judged = {
        "decision": "TAKE",
        "confidence": 10,
        "skeptic_objections_answered": True,
        "skeptic_answer": "A real, sufficiently long rebuttal of the objection.",
        "reason": "x",
    }
    result = enforce_judge_gate(judged, _verdicts(), config)
    assert result["decision"] == "SKIP"
    assert any("confidence" in override for override in result["gate_overrides"])


def test_gate_leaves_a_valid_take_alone(config):
    judged = {
        "decision": "TAKE",
        "confidence": 80,
        "skeptic_objections_answered": True,
        "skeptic_answer": "The offering risk is gone: the raise closed last week at $3.10.",
        "reason": "x",
    }
    result = enforce_judge_gate(judged, _verdicts(), config)
    assert result["decision"] == "TAKE"
    assert "gate_overrides" not in result


# ------------------------------------------------------- prompts and contracts


def test_every_role_prompt_exists_and_documents_its_json_contract():
    directory = agents_dir()
    for role in ROLE_FILES:
        body = load_role_prompt(role, directory)
        assert '"role"' in body or '"decision"' in body
        assert "JSON" in body
        assert not body.startswith("---")


def test_skeptic_prompt_documents_the_inverted_polarity():
    body = load_role_prompt("skeptic", agents_dir())
    assert "objection severity" in body.lower()


def test_judge_prompt_states_the_hard_skeptic_gate():
    body = load_role_prompt("judge", agents_dir())
    assert "SKIP" in body and "skeptic_objections_answered" in body


def test_user_message_carries_the_relevant_context(stock_hit, config):
    context = {
        "config": config,
        "verdicts": {"researcher": {"score": 7}, "technician": {"score": 6}},
        "episodic_pivot": {"composite_score": 70},
    }
    researcher_msg = build_user_message("researcher", stock_hit, context)
    assert "episodic_pivot" in researcher_msg
    judge_msg = build_user_message("judge", stock_hit, context)
    assert "judge_policy" in judge_msg and "researcher" in judge_msg


# ------------------------------------------------------------ full review pass


def test_heuristic_review_of_the_three_fixture_hits(config):
    hits = load_fixture(str(FIXTURE_HITS))
    reviews = review_hits(hits, config, backend="heuristic", offline=True)
    assert len(reviews) == 3
    by_ticker = {review["ticker"]: review for review in reviews}
    # The unexplained, 68%-extended, 12x-volume mover must not become a call.
    assert by_ticker["PMPX"]["decision"] == "SKIP"
    # Every review carries all five verdicts.
    for review in reviews:
        assert set(review["verdicts"]) == {
            "researcher",
            "technician",
            "skeptic",
            "risk_manager",
            "judge",
        }
        assert review["decision"] in {"TAKE", "SKIP"}
        assert 0 <= review["confidence"] <= 100
    assert by_ticker["URAX"]["asset_type"] == "etf"


def test_llm_backend_parses_verdicts_and_records_cost(config, stock_hit, tmp_db):
    replies = [
        json.dumps(
            {
                "role": "researcher",
                "score": 9,
                "catalyst_type": "fda_regulatory",
                "catalyst_summary": "Approval granted 2026-09-18 (company PR).",
                "reasons": ["hard catalyst", "dated source"],
            }
        ),
        json.dumps(
            {"role": "technician", "score": 7, "trend": "uptrend", "reasons": ["clean base"]}
        ),
        json.dumps(
            {
                "role": "skeptic",
                "score": 3,
                "strongest_objection": "Cash runway is short.",
                "objection_category": "dilution",
                "reasons": ["burn"],
            }
        ),
        json.dumps(
            {
                "role": "risk_manager",
                "score": 7,
                "direction": "long",
                "entry": 3.8,
                "stop": 3.3,
                "reasons": ["structural stop"],
            }
        ),
        json.dumps(
            {
                "role": "judge",
                "decision": "TAKE",
                "confidence": 78,
                "reason": "Approval plus tight stop",
                "skeptic_objections_answered": True,
                "skeptic_answer": "The raise closed last week, so the runway objection is stale.",
                "reasons": ["catalyst", "stop"],
            }
        ),
    ]
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(replies))
    prompts = {role: f"{role} system prompt" for role in ROLE_FILES}
    review = review_hit(stock_hit, config, backend="llm", llm=client, prompts=prompts, offline=True)

    assert review["decision"] == "TAKE"
    assert review["confidence"] == 78
    assert review["verdicts"]["researcher"]["backend"] == "llm"
    assert len(client.run_cost.records) == 5
    assert client.run_cost.total_usd > 0
    # The judge ran on the stronger model, the analysts on the cheap one.
    models = [record.model for record in client.run_cost.records]
    assert models[:4] == [config["roles"]["models"]["worker"]] * 4
    assert models[4] == config["roles"]["models"]["judge"]


def test_a_dead_backend_refuses_to_invent_a_verdict(config, stock_hit, tmp_db):
    """The Researcher, Skeptic and Judge are never faked — the hit goes UNREVIEWED."""

    class Boom:
        class messages:  # noqa: N801 - mimics the SDK namespace
            @staticmethod
            def create(**_kwargs):
                raise RuntimeError("503 overloaded")

    client = LLMClient(config, spend_store=tmp_db, client=Boom())
    with pytest.raises(ReviewUnavailable, match="researcher"):
        review_hit(
            stock_hit,
            config,
            backend="llm",
            llm=client,
            prompts={role: "prompt" for role in ROLE_FILES},
            offline=True,
        )


def test_a_non_strict_role_may_still_fall_back(config, stock_hit, tmp_db):
    """The Technician is arithmetic on the screener row, so offline is honest."""
    config = {**config, "roles": {**config["roles"], "llm_only": ["judge"]}}
    replies = [
        json.dumps({"score": 7, "catalyst": "FDA approval", "reasons": ["a", "b"]}),  # researcher
        "not json at all",  # technician — allowed to fall back
        json.dumps({"score": 3, "strongest_objection": "thin float", "reasons": ["c"]}),  # skeptic
        json.dumps({"score": 6, "direction": "long", "instrument": "call"}),  # risk manager
        json.dumps(
            {
                "decision": "SKIP",
                "confidence": 40,
                "reason": "not enough",
                "skeptic_answer": "x" * 30,
                "skeptic_objections_answered": True,
            }
        ),
    ]
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(replies))
    review = review_hit(
        stock_hit,
        config,
        backend="llm",
        llm=client,
        prompts={role: "prompt" for role in ROLE_FILES},
        offline=True,
    )
    assert review["verdicts"]["technician"]["backend"] == "heuristic"
    assert review["verdicts"]["researcher"]["backend"] == "llm"
    assert any("LLM unavailable" in note for note in review["notes"])


def test_a_strict_role_returning_junk_is_not_papered_over(config, stock_hit, tmp_db):
    replies = [json.dumps({"score": 7, "reasons": ["a"]}), "not json", "also not json"]
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(replies))
    with pytest.raises(ReviewUnavailable, match="skeptic"):
        review_hit(
            stock_hit,
            config,
            backend="llm",
            llm=client,
            prompts={role: "prompt" for role in ROLE_FILES},
            offline=True,
        )


def test_malformed_llm_output_is_normalized(config, stock_hit, tmp_db):
    replies = [
        json.dumps({"score": "8.7", "direction": "LONG", "reasons": "single string"})
    ] * 4 + [json.dumps({"decision": "take", "confidence": "1000", "skeptic_answer": "x"})]
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(replies))
    review = review_hit(
        stock_hit,
        config,
        backend="llm",
        llm=client,
        prompts={role: "prompt" for role in ROLE_FILES},
        offline=True,
    )
    technician = review["verdicts"]["technician"]
    assert technician["score"] == 8.7
    assert isinstance(technician["reasons"], list)
    assert review["verdicts"]["risk_manager"]["direction"] == "long"
    # confidence is clamped, and the bogus 'take' is gated on the missing answer
    assert review["confidence"] == 100
    assert review["decision"] == "SKIP"


def test_extract_json_tolerates_prose_and_fences():
    assert extract_json('Here you go:\n```json\n{"a": 1}\n```\nthanks') == {"a": 1}
    assert extract_json('{"nested": {"b": 2}} trailing') == {"nested": {"b": 2}}
    with pytest.raises(ValueError):
        extract_json("no object here")


def test_llm_client_reports_unavailable_without_a_key(config, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = LLMClient(config)
    assert client.available() is False


def test_monthly_cap_blocks_further_calls(config, tmp_db):
    config["llm"]["monthly_spend_cap_usd"] = 0.01
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(['{"score": 5}']))
    tmp_db.record_llm_usage(
        {
            "run_id": "r0",
            "month": __import__("llm_client").current_month(),
            "role": "researcher",
            "model": "claude-haiku-4-5",
            "input_tokens": 1000,
            "output_tokens": 1000,
            "cost_usd": 0.02,
        }
    )
    assert client.available() is False
    assert "cap reached" in client.availability()["reason"]
    with pytest.raises(LLMUnavailable):
        client.complete_json(role="researcher", kind="worker", system="s", user="u")


def test_worker_model_gets_no_thinking_parameters(config, tmp_db):
    fake = FakeAnthropic(['{"score": 5}', '{"score": 5}'])
    client = LLMClient(config, spend_store=tmp_db, client=fake)
    client.complete_json(role="researcher", kind="worker", system="s", user="u")
    client.complete_json(role="judge", kind="judge", system="s", user="u")
    worker_call, judge_call = fake.messages.calls
    assert "thinking" not in worker_call  # Haiku 4.5 rejects adaptive thinking
    assert judge_call["thinking"] == {"type": "adaptive"}
    assert judge_call["output_config"] == {"effort": "medium"}
