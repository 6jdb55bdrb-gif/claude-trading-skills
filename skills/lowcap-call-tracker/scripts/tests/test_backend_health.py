"""Backend health, UNREVIEWED calls, the catalyst penalty and web search."""

import json
from datetime import datetime, timezone

from call_db import DECISION_UNREVIEWED, KIND_ACTIVE, KIND_SHADOW, KIND_UNREVIEWED
from llm_client import LLMClient
from role_review import ReviewUnavailable, apply_catalyst_penalty, web_search_enabled
from run_cycle import _check_backend, review_backlog, run_cycle, unreviewed_review
from stats import compute_stats, format_backend_line, render_markdown

from conftest import FIXTURE_HITS, FakeAnthropic

NOW = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------- health check


class _Boom:
    class messages:  # noqa: N801 - mimics the SDK namespace
        @staticmethod
        def create(**_kwargs):
            raise RuntimeError("401 invalid x-api-key")


def test_health_check_reports_a_working_backend(config, tmp_db):
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(["ok"]))
    health = client.health_check()
    assert health["ok"] is True
    assert health["model"] == config["roles"]["models"]["worker"]
    assert "latency_ms" in health


def test_health_check_names_the_real_failure(config, tmp_db):
    client = LLMClient(config, spend_store=tmp_db, client=_Boom())
    health = client.health_check()
    assert health["ok"] is False
    assert "invalid x-api-key" in health["reason"]
    assert health["stage"] == "request"


def test_health_check_reports_a_missing_package_or_key(config, monkeypatch, tmp_db):
    import llm_client

    monkeypatch.setattr(llm_client, "HAS_ANTHROPIC", False)
    health = LLMClient(config, spend_store=tmp_db).health_check()
    assert health["ok"] is False
    assert "anthropic" in health["reason"]
    assert health["stage"] == "availability"


def test_health_check_reports_a_spent_budget(config, tmp_db):
    config = {**config, "llm": {**config["llm"], "monthly_spend_cap_usd": 0.0001}}
    tmp_db.record_llm_usage(
        {
            "run_id": "r1",
            "created_at": NOW.isoformat(),
            "month": NOW.strftime("%Y-%m"),
            "role": "judge",
            "model": "claude-sonnet-5",
            "input_tokens": 1,
            "output_tokens": 1,
            "cache_read_tokens": 0,
            "cost_usd": 5.0,
        }
    )
    health = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(["ok"])).health_check()
    assert health["ok"] is False
    assert "cap" in health["reason"]


def test_the_cycle_checks_the_backend_before_using_it(config, tmp_db):
    client = LLMClient(config, spend_store=tmp_db, client=_Boom())
    health = _check_backend(client, config, "llm")
    assert health["ok"] is False
    assert health["checked"] is True


def test_the_health_check_can_be_turned_off(config, tmp_db):
    config = {**config, "roles": {**config["roles"], "health_check": False}}
    client = LLMClient(config, spend_store=tmp_db, client=FakeAnthropic(["ok"]))
    health = _check_backend(client, config, "llm")
    assert health["checked"] is False
    assert health["ok"] is True


# --------------------------------------------------------------- web search


def test_only_the_researcher_searches(config):
    assert web_search_enabled(config, "researcher") is True
    for role in ("technician", "skeptic", "risk_manager", "judge"):
        assert web_search_enabled(config, role) is False


def test_the_researcher_call_carries_the_search_tool(config, tmp_db):
    fake = FakeAnthropic([json.dumps({"score": 7, "reasons": ["a"]})])
    client = LLMClient(config, spend_store=tmp_db, client=fake)
    client.complete_json(role="researcher", kind="worker", system="s", user="u", web_search=True)
    tools = fake.calls[0]["tools"]
    assert tools[0]["name"] == "web_search"
    assert tools[0]["type"] == "web_search_20250305"
    assert tools[0]["max_uses"] == config["roles"]["web_search"]["max_uses"]


def test_other_roles_get_no_tools(config, tmp_db):
    fake = FakeAnthropic([json.dumps({"score": 7})])
    client = LLMClient(config, spend_store=tmp_db, client=fake)
    client.complete_json(role="skeptic", kind="worker", system="s", user="u")
    assert "tools" not in fake.calls[0]


def test_searches_are_billed_on_top_of_tokens(config, tmp_db):
    fake = FakeAnthropic([json.dumps({"score": 7})], web_search_requests=3)
    client = LLMClient(config, spend_store=tmp_db, client=fake)
    _verdict, record = client.complete_json(
        role="researcher", kind="worker", system="s", user="u", web_search=True
    )
    assert record.web_searches == 3
    # 3 searches at $10 per 1000
    assert record.cost_usd >= 0.03
    assert client.run_cost.summary()["web_searches"] == 3


# ----------------------------------------------------------- unreviewed calls


def test_a_hit_recorded_while_the_backend_is_down_claims_nothing(stock_hit):
    review = unreviewed_review(stock_hit, "401 invalid x-api-key")
    assert review["decision"] == DECISION_UNREVIEWED
    assert review["confidence"] is None
    assert review["direction"] is None
    assert review["verdicts"] == {}
    assert "401" in review["notes"][0]


def test_an_unreviewed_call_is_stored_and_kept_out_of_judge_stats(tmp_db, config, stock_hit):
    call_id = tmp_db.insert_call(unreviewed_review(stock_hit, "backend down"), run_id="r1")
    assert call_id is not None
    row = dict(tmp_db.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone())
    assert row["kind"] == KIND_UNREVIEWED
    assert row["judge_decision"] == DECISION_UNREVIEWED
    assert row["reviewed_at"] is None
    assert row["hit_json"]  # kept so it can be reviewed later

    stats = compute_stats(tmp_db, config)
    assert stats["overall"]["total"] == 1
    assert stats["overall"]["unreviewed_calls"] == 1
    assert stats["overall"]["reviewed_calls"] == 0
    assert stats["take_vs_skip"]["take"]["total"] == 0
    assert stats["take_vs_skip"]["skip_shadow"]["total"] == 0
    assert all(block["samples"] == 0 for block in stats["role_accuracy"].values())
    assert all(block["total"] == 0 for block in stats["confidence_buckets"].values())


def test_a_late_review_keeps_the_original_entry(tmp_db, config, stock_hit, review_fn):
    call_id = tmp_db.insert_call(unreviewed_review(stock_hit, "backend down"), run_id="r1")
    before = dict(tmp_db.conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone())

    updated = tmp_db.apply_review(call_id, review_fn("SQZX", decision="TAKE"), run_id="r2")
    assert updated["entry_price"] == before["entry_price"]
    assert updated["call_date"] == before["call_date"]
    assert updated["judge_decision"] == "TAKE"
    assert updated["kind"] == KIND_ACTIVE
    assert updated["reviewed_at"] is not None
    assert updated["review_run_id"] == "r2"


def test_a_late_skip_becomes_a_shadow_call(tmp_db, review_fn, stock_hit):
    call_id = tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
    updated = tmp_db.apply_review(call_id, review_fn("SQZX", decision="SKIP"), run_id="r2")
    assert updated["kind"] == KIND_SHADOW


def test_the_backlog_is_reviewed_on_the_next_healthy_run(tmp_db, config, stock_hit, monkeypatch):
    import run_cycle as rc

    tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")

    def fake_review(hit, cfg, **_kw):
        return {
            "ticker": hit["ticker"],
            "decision": "TAKE",
            "confidence": 72,
            "verdicts": {"risk_manager": {"direction": "long", "instrument": "call"}},
            "backend": "llm",
        }

    monkeypatch.setattr(rc, "review_hit", fake_review)
    monkeypatch.setattr(rc, "load_role_prompts", lambda *_a, **_k: {"judge": "p"})
    result = review_backlog(
        tmp_db,
        config,
        run_id="r2",
        backend="llm",
        llm=None,
        agents_dir=None,
        offline=True,
        dry_run=False,
    )
    assert result["pending"] == 1
    assert result["reviewed"][0]["decision"] == "TAKE"
    assert tmp_db.unreviewed_calls() == []


def test_a_backlog_review_that_fails_leaves_the_call_unreviewed(
    tmp_db, config, stock_hit, monkeypatch
):
    import run_cycle as rc

    tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")

    def boom(*_a, **_kw):
        raise ReviewUnavailable("researcher: still down")

    monkeypatch.setattr(rc, "review_hit", boom)
    monkeypatch.setattr(rc, "load_role_prompts", lambda *_a, **_k: {"judge": "p"})
    result = review_backlog(
        tmp_db,
        config,
        run_id="r2",
        backend="llm",
        llm=None,
        agents_dir=None,
        offline=True,
        dry_run=False,
    )
    assert result["failed"][0]["reason"] == "researcher: still down"
    assert len(tmp_db.unreviewed_calls()) == 1


def test_a_dead_backend_still_screens_and_tracks(tmp_path, config, monkeypatch):
    """The screener's own edge stays measurable while the roles are down."""
    import run_cycle as rc

    monkeypatch.setattr(
        rc, "_check_backend", lambda *_a, **_k: {"ok": False, "reason": "no key", "checked": True}
    )
    config = {
        **config,
        "tracker": {
            **config["tracker"],
            "stats_file": str(tmp_path / "stats.md"),
            "improvements_file": str(tmp_path / "improvements.md"),
            "reports_dir": str(tmp_path / "reports"),
        },
    }
    report = run_cycle(
        config,
        backend="llm",
        offline=True,
        fixture=str(FIXTURE_HITS),
        prices={},
        force_screen=True,
        telegram=False,
        db_path=str(tmp_path / "down.db"),
        now=NOW,
    )
    assert report["backend_health"]["ok"] is False
    assert any("BACKEND DOWN" in error or "backend DOWN" in error for error in report["errors"])
    assert report["unreviewed"] == len(report["new_calls"])
    assert all(call["decision"] == DECISION_UNREVIEWED for call in report["new_calls"])

    stats_text = (tmp_path / "stats.md").read_text()
    assert "BACKEND DOWN" in stats_text


# ------------------------------------------------------------ catalyst penalty


def _judge(confidence=70, decision="TAKE"):
    return {
        "decision": decision,
        "confidence": confidence,
        "reason": "structure is clean",
        "skeptic_answer": "x" * 40,
        "skeptic_objections_answered": True,
    }


def test_no_catalyst_costs_confidence_but_does_not_force_a_skip(config):
    verdicts = {"researcher": {"score": 2.0}}
    judged = apply_catalyst_penalty(_judge(confidence=90), verdicts, config)
    assert judged["decision"] == "TAKE"
    assert judged["confidence"] == 90 - config["roles"]["judge"]["no_catalyst_penalty"]
    assert judged["catalyst_penalty"]["points"] == 15


def test_a_real_catalyst_is_not_penalized(config):
    verdicts = {"researcher": {"score": 8.0}}
    judged = apply_catalyst_penalty(_judge(confidence=70), verdicts, config)
    assert judged["confidence"] == 70
    assert "catalyst_penalty" not in judged


def test_a_thin_catalyst_can_still_lose_the_confidence_gate(config):
    """The penalty decides nothing by itself; the usual threshold still applies."""
    from role_review import enforce_judge_gate

    verdicts = {"researcher": {"score": 1.0}, "risk_manager": {"direction": "long"}}
    judged = apply_catalyst_penalty(_judge(confidence=60), verdicts, config)
    judged = enforce_judge_gate(judged, verdicts, config)
    assert judged["confidence"] == 45
    assert judged["decision"] == "SKIP"
    assert "below threshold" in judged["gate_overrides"][0]


def test_a_strong_setup_survives_a_missing_catalyst(config):
    from role_review import enforce_judge_gate

    verdicts = {"researcher": {"score": 1.0}, "risk_manager": {"direction": "long"}}
    judged = apply_catalyst_penalty(_judge(confidence=95), verdicts, config)
    judged = enforce_judge_gate(judged, verdicts, config)
    assert judged["decision"] == "TAKE"
    assert judged["confidence"] == 80


def test_the_gate_keeps_the_judges_own_reasoning(config):
    from role_review import enforce_judge_gate

    verdicts = {"risk_manager": {"direction": "none"}}
    judged = enforce_judge_gate(_judge(), verdicts, config)
    assert judged["decision"] == "SKIP"
    assert judged["judge_reason"] == "structure is clean"
    assert "no executable plan" in judged["reason"]


# -------------------------------------------------------------------- stats


def test_the_backend_line_leads_the_statistics(tmp_db, config, stock_hit, review_fn):
    tmp_db.insert_call(unreviewed_review(stock_hit, "down"), run_id="r1")
    tmp_db.insert_call(review_fn("AAA", decision="TAKE"), run_id="r1")
    tmp_db.insert_call(review_fn("BBB", decision="SKIP"), run_id="r1")

    stats = compute_stats(tmp_db, config, backend_health={"ok": True, "reason": "ok"})
    line = format_backend_line(stats["backend"])
    assert "UP" in line
    assert "reviewed 2" in line
    assert "unreviewed 1" in line
    assert "TAKE/SKIP 1/1" in line
    assert render_markdown(stats).splitlines()[2].startswith("**Backend:**")


def test_a_down_backend_is_shouted_at_the_top(tmp_db, config):
    stats = compute_stats(tmp_db, config, backend_health={"ok": False, "reason": "no credit"})
    markdown = render_markdown(stats)
    assert "BACKEND DOWN" in markdown
    assert "no credit" in markdown


# ---------------------------------------------------------- judge strictness


def test_a_judge_that_skips_everything_is_flagged(tmp_db, config, review_fn):
    from learning_loop import analyse, judge_strictness

    for index in range(20):
        tmp_db.insert_call(review_fn(f"T{index:02d}", decision="SKIP"), run_id="r1")
    strictness = judge_strictness(tmp_db, config)
    assert strictness["skip_pct"] == 100.0
    assert strictness["flagged"] is True

    findings = [p["finding"] for p in analyse(tmp_db, config)["proposals"] if "finding" in p]
    assert any("Judge too strict?" in finding for finding in findings)


def test_a_balanced_judge_is_not_flagged(tmp_db, config, review_fn):
    from learning_loop import judge_strictness

    for index in range(16):
        tmp_db.insert_call(review_fn(f"S{index:02d}", decision="SKIP"), run_id="r1")
    for index in range(4):
        tmp_db.insert_call(review_fn(f"T{index:02d}", decision="TAKE"), run_id="r1")
    assert judge_strictness(tmp_db, config)["flagged"] is False


def test_unreviewed_calls_are_not_blamed_on_the_judge(tmp_db, config, stock_hit, review_fn):
    """A backend outage must not read as a strict Judge."""
    from learning_loop import judge_strictness

    for index in range(15):
        hit = {**stock_hit, "ticker": f"U{index:02d}"}
        tmp_db.insert_call(unreviewed_review(hit, "down"), run_id="r1")
    for index in range(5):
        tmp_db.insert_call(review_fn(f"T{index:02d}", decision="TAKE"), run_id="r1")
    strictness = judge_strictness(tmp_db, config)
    assert strictness["sample"] == 5
    assert strictness["skip_pct"] == 0.0
    assert strictness["flagged"] is False


# --------------------------------------------------------------- .env loading


def test_dotenv_loads_without_overriding_the_real_environment(tmp_path, monkeypatch):
    from config import load_dotenv

    env = tmp_path / ".env"
    env.write_text(
        "# a comment\nANTHROPIC_API_KEY=from-file\nexport OTHER_KEY='quoted'\nbroken line\n"
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-environment")
    monkeypatch.delenv("OTHER_KEY", raising=False)

    loaded = load_dotenv(env)
    assert "OTHER_KEY" in loaded
    assert "ANTHROPIC_API_KEY" not in loaded  # the real environment wins
    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "from-environment"
    assert os.environ["OTHER_KEY"] == "quoted"


def test_dotenv_is_a_no_op_when_absent(tmp_path):
    from config import load_dotenv

    assert load_dotenv(tmp_path / "nope.env") == []


def test_an_unreviewed_call_renders_without_crashing(stock_hit, tmp_db, config):
    """An UNREVIEWED call has no confidence, direction or stop to print."""
    from run_cycle import _call_line, format_report

    review = unreviewed_review(stock_hit, "no key")
    report = {
        "run_id": "r1",
        "session": {"as_of": "2026-09-21T15:00:00-04:00", "reason": "regular trading hours"},
        "screening_ran": True,
        "llm": {"available": False, "reason": "ANTHROPIC_API_KEY is not set"},
        "backend_health": {"ok": False, "reason": "ANTHROPIC_API_KEY is not set", "checked": True},
        "new_calls": [{**_call_line(review), "call_id": 1}],
        "duplicates_skipped": [],
        "price_update": {"priced": 0, "closed": 0, "updates": [], "missing_prices": []},
        "reviews": [],
        "errors": [],
        "stats": compute_stats(tmp_db, config, backend_health={"ok": False, "reason": "x"}),
        "llm_cost": {"cost_usd": 0.0, "calls": 0, "input_tokens": 0, "output_tokens": 0},
        "llm_month_to_date_usd": 0.0,
        "llm_cap_usd": 10.0,
    }
    text = format_report(report)
    assert "UNREVIEWED" in text
    assert "SQZX" in text
    assert "DOWN" in text
    # An empty tracker reads in words and dashes, never "hit_rate=None%".
    assert "None" not in text
