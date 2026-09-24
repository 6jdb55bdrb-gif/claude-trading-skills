#!/usr/bin/env python3
"""Run the five-role review over screener hits and return TAKE / SKIP verdicts.

Roles are defined once, in ``agents/lowcap-*.md``: the same files Claude Code
loads as subagents are the system prompts sent to the Anthropic API on the
server. Two backends implement them:

* ``llm``       — Anthropic Messages API (cheap model for the four analysts,
                  stronger model for the Judge), via ``llm_client``.
* ``heuristic`` — deterministic offline scoring (``heuristic_roles``).

``auto`` uses the LLM backend when the SDK, the key and the monthly budget all
allow it, and falls back to the heuristic per role on any failure. The Judge gate
(Skeptic answered, plan exists, confidence floor) is enforced in code so a
hallucinated TAKE cannot slip through either backend.

CLI (dry run):
    python3 role_review.py --fixture fixtures/dry_run_hits.json --backend heuristic
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import heuristic_roles as heuristic
from llm_client import LLMClient, LLMUnavailable
from skill_adapters import fetch_daily_bars, run_episodic_pivot, run_position_sizer
from skill_adapters import run_weekly_price_action as weekly_adapter

from config import load_config, load_dotenv, repo_root

ROLE_FILES = {
    "researcher": "lowcap-researcher.md",
    "technician": "lowcap-technician.md",
    "skeptic": "lowcap-skeptic.md",
    "risk_manager": "lowcap-risk-manager.md",
    "judge": "lowcap-judge.md",
}
WORKER_ROLES = ("researcher", "technician", "skeptic", "risk_manager")
ROLE_KIND = {role: "worker" for role in WORKER_ROLES} | {"judge": "judge"}


class RolePromptError(RuntimeError):
    """Raised when a role prompt file cannot be located."""


def agents_dir(explicit: str | None = None) -> Path:
    """Locate the directory holding the ``lowcap-*.md`` role prompts."""
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(repo_root() / "agents")
    candidates.append(Path(__file__).resolve().parents[1] / "references" / "roles")
    for candidate in candidates:
        if (candidate / ROLE_FILES["judge"]).is_file():
            return candidate
    raise RolePromptError(
        "role prompts not found. Looked in: "
        + ", ".join(str(candidate) for candidate in candidates)
        + ". Pass --agents-dir pointing at the directory holding lowcap-*.md."
    )


def load_role_prompt(role: str, directory: Path) -> str:
    """Return the prompt body of a role file, with YAML frontmatter stripped."""
    path = directory / ROLE_FILES[role]
    text = path.read_text(encoding="utf-8")
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()


def _compact(hit: dict[str, Any]) -> dict[str, Any]:
    """The screener fields worth spending tokens on."""
    keys = (
        "ticker",
        "company",
        "asset_type",
        "variant",
        "sector",
        "industry",
        "price",
        "change_pct",
        "rel_volume",
        "avg_volume",
        "volume",
        "market_cap",
        "float_shares",
        "short_float_pct",
        "short_ratio",
        "inst_own_pct",
        "insider_trans_pct",
        "sma20_pct",
        "sma50_pct",
        "sma200_pct",
        "high52w_pct",
        "low52w_pct",
        "rsi",
        "atr",
        "beta",
        "gap_pct",
        "perf_week_pct",
        "perf_month_pct",
        "catalyst_headline",
    )
    return {key: hit[key] for key in keys if hit.get(key) is not None}


def build_user_message(role: str, hit: dict[str, Any], context: dict[str, Any]) -> str:
    """Render the per-role user message."""
    payload: dict[str, Any] = {"screener_hit": _compact(hit)}
    if role == "researcher" and context.get("episodic_pivot"):
        payload["episodic_pivot"] = context["episodic_pivot"]
    if role == "technician" and context.get("weekly_price_action"):
        payload["weekly_price_action"] = context["weekly_price_action"]
    if role in {"skeptic", "risk_manager", "judge"}:
        payload["verdicts"] = {
            name: context["verdicts"][name]
            for name in WORKER_ROLES
            if name in context.get("verdicts", {}) and name != role
        }
    if role == "risk_manager":
        payload["risk_inputs"] = {
            "account_size": context["config"]["tracker"]["account_size"],
            "risk_pct": context["config"]["tracker"]["risk_pct"],
            "max_position_pct": context["config"]["tracker"].get("max_position_pct"),
        }
        if context.get("position_sizer"):
            payload["position_sizer"] = context["position_sizer"]
    if role == "judge":
        payload["verdicts"] = context.get("verdicts", {})
        payload["judge_policy"] = context["config"]["roles"].get("judge", {})

    return (
        "Review this screener hit and return only the JSON object your output "
        "contract defines.\n\n" + json.dumps(payload, indent=2, sort_keys=True, default=str)
    )


def _heuristic_verdict(role: str, hit: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    verdicts = context.get("verdicts", {})
    if role == "researcher":
        return heuristic.researcher(hit, episodic_pivot=context.get("episodic_pivot"))
    if role == "technician":
        return heuristic.technician(hit, weekly=context.get("weekly_price_action"))
    if role == "skeptic":
        return heuristic.skeptic(
            hit,
            researcher_verdict=verdicts.get("researcher"),
            technician_verdict=verdicts.get("technician"),
        )
    if role == "risk_manager":
        return heuristic.risk_manager(
            hit,
            technician_verdict=verdicts.get("technician"),
            skeptic_verdict=verdicts.get("skeptic"),
            researcher_verdict=verdicts.get("researcher"),
            config=context["config"],
            sizing=context.get("position_sizer"),
        )
    return heuristic.judge(verdicts, config=context["config"])


def short_allowed(config: dict[str, Any] | None) -> bool:
    """Whether a bearish plan may be proposed at all.

    Off by default. These names have no listed options and are hard to borrow,
    so a short thesis cannot be executed — and an inexecutable call in the
    record is worse than no call, because it collects PnL nobody could have had.
    """
    return bool(((config or {}).get("roles") or {}).get("allow_short", False))


def _normalize_verdict(
    role: str, verdict: dict[str, Any], *, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Coerce an LLM verdict into the stored contract (types, bounds, defaults)."""
    verdict = dict(verdict)
    verdict["role"] = role
    reasons = verdict.get("reasons")
    if isinstance(reasons, str):
        reasons = [reasons]
    verdict["reasons"] = [str(item) for item in (reasons or [])][:3]

    if role == "judge":
        decision = str(verdict.get("decision", "SKIP")).strip().upper()
        verdict["decision"] = "TAKE" if decision == "TAKE" else "SKIP"
        try:
            confidence = int(round(float(verdict.get("confidence", 0))))
        except (TypeError, ValueError):
            confidence = 0
        verdict["confidence"] = max(0, min(100, confidence))
        verdict["skeptic_objections_answered"] = bool(verdict.get("skeptic_objections_answered"))
        verdict["reason"] = str(verdict.get("reason", ""))[:140]
        return verdict

    try:
        score = float(verdict.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    verdict["score"] = round(max(0.0, min(10.0, score)), 1)
    if role == "risk_manager":
        direction = str(verdict.get("direction", "none")).strip().lower()
        verdict["direction"] = direction if direction in {"long", "short", "none"} else "none"
        instrument = str(verdict.get("instrument", "")).strip().lower()
        if instrument not in {"call", "put", "none"}:
            instrument = (
                "none"
                if verdict["direction"] == "none"
                else ("put" if verdict["direction"] == "short" else "call")
            )
        if instrument == "put" or verdict["direction"] == "short":
            if not short_allowed(config):
                # Neutralized, not silently flipped to a long: the setup the
                # Risk Manager saw was bearish, and pretending otherwise would
                # invent a thesis nobody argued. "none" makes it a SKIP.
                verdict["instrument"] = "none"
                verdict["direction"] = "none"
                verdict["reasons"] = (
                    verdict["reasons"]
                    + ["bearish setup, but a short is not executable on this name"]
                )[:3]
                verdict["short_suppressed"] = True
                return verdict
        verdict["instrument"] = instrument
    return verdict


def apply_catalyst_penalty(
    judge_verdict: dict[str, Any],
    verdicts: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Charge a missing catalyst confidence, and let the Judge weigh the rest.

    A thin news tape is a reason to want more, not a veto: a clean structure
    with a tight stop can still deserve a position. So "no catalyst" costs
    ``roles.judge.no_catalyst_penalty`` points and the remaining confidence
    faces the same threshold as everything else.
    """
    policy = config["roles"].get("judge", {})
    penalty = float(policy.get("no_catalyst_penalty", 0) or 0)
    floor = float(policy.get("catalyst_score_floor", 4.0))
    if penalty <= 0:
        return judge_verdict
    researcher_score = (verdicts.get("researcher") or {}).get("score")
    if researcher_score is None or float(researcher_score) >= floor:
        return judge_verdict

    before = int(judge_verdict.get("confidence") or 0)
    judge_verdict["confidence"] = max(0, before - int(penalty))
    judge_verdict["catalyst_penalty"] = {
        "researcher_score": float(researcher_score),
        "floor": floor,
        "points": int(penalty),
        "confidence_before": before,
        "confidence_after": judge_verdict["confidence"],
    }
    return judge_verdict


def enforce_judge_gate(
    judge_verdict: dict[str, Any],
    verdicts: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Apply the non-negotiable Judge rules, whichever backend produced it."""
    policy = config["roles"].get("judge", {})
    minimum = int(policy.get("min_confidence_to_take", 55))
    overrides: list[str] = []

    if judge_verdict["decision"] == "TAKE":
        direction = (verdicts.get("risk_manager") or {}).get("direction")
        if direction in {None, "none"}:
            judge_verdict["decision"] = "SKIP"
            overrides.append("no executable plan: Risk Manager direction is 'none'")
        answered = bool(judge_verdict.get("skeptic_objections_answered"))
        answer = str(judge_verdict.get("skeptic_answer") or "").strip()
        if policy.get("require_skeptic_answer", True) and (not answered or len(answer) < 20):
            judge_verdict["decision"] = "SKIP"
            overrides.append("Skeptic objection not explicitly answered")
        if judge_verdict["confidence"] < minimum:
            judge_verdict["decision"] = "SKIP"
            overrides.append(f"confidence {judge_verdict['confidence']} below threshold {minimum}")

    if overrides:
        judge_verdict["gate_overrides"] = overrides
        # Keep what the Judge actually argued: the gate says which rule fired,
        # the Judge's own reasoning says why it wanted what it wanted, and both
        # belong in the record.
        judge_verdict.setdefault("judge_reason", judge_verdict.get("reason"))
        judge_verdict["reason"] = f"SKIP — {overrides[0]}"[:140]
    return judge_verdict


def gather_context(
    hit: dict[str, Any],
    config: dict[str, Any],
    *,
    offline: bool = False,
) -> dict[str, Any]:
    """Run the sibling-skill adapters that feed the roles."""
    reuse = config["roles"].get("reuse", {})
    context: dict[str, Any] = {"config": config, "verdicts": {}, "adapter_notes": []}
    bars: list[dict[str, Any]] = []

    if not offline and (reuse.get("weekly_price_action") or reuse.get("episodic_pivot_analyzer")):
        bars = fetch_daily_bars(hit["ticker"])
        if not bars:
            context["adapter_notes"].append("no daily bars available (yfinance missing or empty)")

    if reuse.get("episodic_pivot_analyzer"):
        result = run_episodic_pivot(
            hit,
            headline=hit.get("catalyst_headline"),
            as_of=hit.get("screened_at", date.today().isoformat())[:10],
            bars=bars or None,
        )
        if result and result.get("error"):
            context["adapter_notes"].append(result["error"])
        elif result:
            context["episodic_pivot"] = dict(result)

    if reuse.get("weekly_price_action") and bars:
        result = weekly_adapter(hit, bars)
        if result and result.get("error"):
            context["adapter_notes"].append(result["error"])
        elif result:
            context["weekly_price_action"] = dict(result)

    return context


class ReviewUnavailable(RuntimeError):
    """Raised when a role that may not be faked could not be run.

    The caller records the hit as UNREVIEWED. A deterministic guess about a
    catalyst, an objection or a verdict would read exactly like a real opinion
    in the statistics, which is the one thing the tracker must never publish.
    """


def llm_only_roles(config: dict[str, Any]) -> set[str]:
    """Roles whose verdict must come from the LLM or not at all."""
    configured = config["roles"].get("llm_only", ["researcher", "skeptic", "judge"])
    return {str(role).lower() for role in configured}


def web_search_enabled(config: dict[str, Any], role: str) -> bool:
    """Only the RESEARCHER searches: the others reason about what it found."""
    if role != "researcher":
        return False
    return bool((config["roles"].get("web_search") or {}).get("enabled", True))


def review_hit(
    hit: dict[str, Any],
    config: dict[str, Any],
    *,
    backend: str = "auto",
    llm: LLMClient | None = None,
    prompts: dict[str, str] | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Run all five roles for one hit and return the assembled review.

    Raises :class:`ReviewUnavailable` when a role in ``roles.llm_only`` cannot
    be answered by the LLM backend.
    """
    context = gather_context(hit, config, offline=offline)
    prompts = prompts or {}
    use_llm = backend == "llm" or (backend == "auto" and llm is not None and llm.available())
    strict = llm_only_roles(config) if backend != "heuristic" else set()
    backend_notes: list[str] = []

    def run_role(role: str) -> dict[str, Any]:
        if use_llm and llm is not None and prompts.get(role):
            try:
                verdict, _usage = llm.complete_json(
                    role=role,
                    kind=ROLE_KIND[role],
                    system=prompts[role],
                    user=build_user_message(role, hit, context),
                    web_search=web_search_enabled(config, role),
                )
                verdict = _normalize_verdict(role, verdict, config=config)
                verdict["backend"] = "llm"
                return verdict
            except (LLMUnavailable, ValueError) as exc:
                if role in strict:
                    raise ReviewUnavailable(f"{role}: {exc}") from exc
                backend_notes.append(f"{role}: LLM unavailable ({exc}); used heuristic")
        elif role in strict:
            reason = "no prompt file" if not prompts.get(role) else "LLM backend unavailable"
            raise ReviewUnavailable(f"{role}: {reason}")
        verdict = _heuristic_verdict(role, hit, context)
        return _normalize_verdict(role, verdict, config=config)

    for role in ("researcher", "technician", "skeptic"):
        context["verdicts"][role] = run_role(role)

    # Size the position before the Risk Manager speaks, so both backends see it.
    if config["roles"].get("reuse", {}).get("position_sizer") and not offline:
        tech = context["verdicts"]["technician"]
        entry = heuristic._num(hit.get("price"))
        support = heuristic._num(tech.get("support"))
        if entry and support and 0 < support < entry:
            sizing = run_position_sizer(
                entry=entry, stop=support, config=config, sector=hit.get("sector")
            )
            if sizing and sizing.get("error"):
                context["adapter_notes"].append(sizing["error"])
            elif sizing:
                context["position_sizer"] = dict(sizing)

    context["verdicts"]["risk_manager"] = run_role("risk_manager")
    judge_verdict = run_role("judge")
    judge_verdict = apply_catalyst_penalty(judge_verdict, context["verdicts"], config)
    judge_verdict = enforce_judge_gate(judge_verdict, context["verdicts"], config)
    context["verdicts"]["judge"] = judge_verdict

    return {
        "ticker": hit["ticker"],
        "asset_type": hit.get("asset_type", "stock"),
        "variant": hit.get("variant"),
        "price": hit.get("price"),
        "hit": hit,
        "verdicts": context["verdicts"],
        "decision": judge_verdict["decision"],
        "confidence": judge_verdict["confidence"],
        "direction": context["verdicts"]["risk_manager"].get("direction"),
        "entry": context["verdicts"]["risk_manager"].get("entry") or hit.get("price"),
        "stop": context["verdicts"]["risk_manager"].get("stop"),
        "instrument": context["verdicts"]["risk_manager"].get("instrument"),
        "strike": context["verdicts"]["risk_manager"].get("strike"),
        "expiry_date": context["verdicts"]["risk_manager"].get("expiry_date"),
        "backend": "llm"
        if use_llm and not backend_notes
        else ("heuristic" if not use_llm else "mixed"),
        "notes": context["adapter_notes"] + backend_notes,
        "episodic_pivot": context.get("episodic_pivot"),
        "weekly_price_action": context.get("weekly_price_action"),
    }


def load_role_prompts(agents_path: str | None = None, *, backend: str = "auto") -> dict[str, str]:
    """Load every role prompt once. Empty when the heuristic backend is asked for."""
    if backend not in {"auto", "llm"}:
        return {}
    try:
        directory = agents_dir(agents_path)
        return {role: load_role_prompt(role, directory) for role in ROLE_FILES}
    except (RolePromptError, OSError) as exc:
        if backend == "llm":
            raise
        print(f"WARNING: {exc}", file=sys.stderr)
        return {}


def review_hits(
    hits: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    backend: str = "auto",
    llm: LLMClient | None = None,
    agents_path: str | None = None,
    offline: bool = False,
) -> list[dict[str, Any]]:
    """Review every hit, loading the role prompts once."""
    prompts = load_role_prompts(agents_path, backend=backend)
    return [
        review_hit(hit, config, backend=backend, llm=llm, prompts=prompts, offline=offline)
        for hit in hits
    ]


def format_review(review: dict[str, Any]) -> str:
    """One-screen human summary of a single review."""
    verdicts = review["verdicts"]
    lines = [
        f"{review['ticker']} ({review['asset_type']}, {review['variant']}) "
        f"price={review.get('price')}",
        f"  RESEARCHER   {verdicts['researcher']['score']:>4}  "
        f"{verdicts['researcher'].get('catalyst_type')}: {verdicts['researcher']['reasons'][0] if verdicts['researcher']['reasons'] else ''}",
        f"  TECHNICIAN   {verdicts['technician']['score']:>4}  "
        f"{verdicts['technician'].get('trend')}, {verdicts['technician'].get('volume_pattern')}: "
        f"{verdicts['technician']['reasons'][0] if verdicts['technician']['reasons'] else ''}",
        f"  SKEPTIC      {verdicts['skeptic']['score']:>4}  (severity) "
        f"{verdicts['skeptic'].get('objection_category')}: {verdicts['skeptic'].get('strongest_objection')}",
        f"  RISK MANAGER {verdicts['risk_manager']['score']:>4}  "
        f"{str(verdicts['risk_manager'].get('instrument') or '-').upper()} "
        f"{verdicts['risk_manager'].get('strike')} exp {verdicts['risk_manager'].get('expiry_date')} "
        f"({verdicts['risk_manager'].get('dte')}d) entry={verdicts['risk_manager'].get('entry')} "
        f"stop={verdicts['risk_manager'].get('stop')}",
        f"  JUDGE        {review['decision']} ({review['confidence']}) — {verdicts['judge'].get('reason')}",
        f"    skeptic answered: {verdicts['judge'].get('skeptic_objections_answered')} — "
        f"{verdicts['judge'].get('skeptic_answer')}",
    ]
    judge = verdicts["judge"]
    if judge.get("reasoning"):
        lines.append(f"    reasoning: {judge['reasoning']}")
    if judge.get("catalyst_penalty"):
        penalty = judge["catalyst_penalty"]
        lines.append(
            f"    catalyst penalty: -{penalty['points']} "
            f"({penalty['confidence_before']} -> {penalty['confidence_after']}, "
            f"researcher {penalty['researcher_score']} below {penalty['floor']})"
        )
    if judge.get("gate_overrides"):
        for override in judge["gate_overrides"]:
            lines.append(f"    gate: {override}")
    for note in review.get("notes", []):
        lines.append(f"    note: {note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # credentials may live in .env; a real env var still wins
    parser = argparse.ArgumentParser(description="Run the lowcap five-role review")
    parser.add_argument("--config")
    parser.add_argument("--fixture", help="JSON file of screener hits to review")
    parser.add_argument("--variant", help="Screen this variant live instead of using a fixture")
    parser.add_argument("--backend", choices=["auto", "llm", "heuristic"], default="auto")
    parser.add_argument("--agents-dir", help="Directory holding lowcap-*.md role prompts")
    parser.add_argument("--offline", action="store_true", help="Skip network-dependent adapters")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if args.fixture:
        from fetch_screener import load_fixture

        hits = load_fixture(args.fixture)
    elif args.variant:
        from fetch_screener import screen_variant

        hits = screen_variant(config, args.variant)
    else:
        print("ERROR: pass --fixture or --variant", file=sys.stderr)
        return 1

    llm = LLMClient(config) if args.backend in {"auto", "llm"} else None
    if args.backend == "llm" and llm is not None and not llm.available():
        print(f"ERROR: LLM backend unavailable: {llm.availability()['reason']}", file=sys.stderr)
        return 2

    reviews = review_hits(
        hits,
        config,
        backend=args.backend,
        llm=llm,
        agents_path=args.agents_dir,
        offline=args.offline or args.backend == "heuristic",
    )

    if args.json:
        print(json.dumps(reviews, indent=2, default=str))
        return 0
    for review in reviews:
        print(format_review(review))
        print()
    takes = sum(1 for review in reviews if review["decision"] == "TAKE")
    print(f"{takes} TAKE / {len(reviews) - takes} SKIP out of {len(reviews)} reviewed")
    if llm is not None and llm.run_cost.records:
        print(f"LLM cost this run: ${llm.run_cost.total_usd:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
