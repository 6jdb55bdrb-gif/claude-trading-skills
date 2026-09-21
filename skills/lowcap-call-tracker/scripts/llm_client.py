#!/usr/bin/env python3
"""Anthropic Messages API wrapper with per-run cost logging and a monthly cap.

Two model tiers, both configurable under ``roles.models``:

* ``worker`` — RESEARCHER / TECHNICIAN / SKEPTIC / RISK MANAGER (cheap model)
* ``judge``  — JUDGE (stronger model)

Spend is priced from ``llm.prices_per_mtok`` and persisted by the caller-supplied
*spend store* (``call_db.CallDatabase`` implements it). Once month-to-date spend
reaches ``llm.monthly_spend_cap_usd`` the client reports itself unavailable
instead of silently spending more.

``health_check()`` proves the backend works with one tiny call before a run
commits to it. Nothing here falls back: a caller that cannot reach the API is
told so, loudly, and decides what to do — the tracker records the screener hits
as UNREVIEWED rather than inventing an opinion about them.

The RESEARCHER is given Anthropic's server-side ``web_search`` tool, because a
catalyst cannot be found in screener fields — it lives in news, filings and
press releases.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:  # pragma: no cover - offline installs take the heuristic path
    HAS_ANTHROPIC = False

# Models that reject `thinking` / `output_config.effort`.
_NO_THINKING_PREFIXES = ("claude-haiku",)

# Anthropic's server-side web search tool. The model issues the searches and the
# API runs them, so no search API key of our own is involved.
WEB_SEARCH_TOOL_VERSION = "web_search_20250305"

# The smallest call that still exercises auth, network, model access and quota.
HEALTH_CHECK_PROMPT = "Reply with the single word: ok"
HEALTH_CHECK_MAX_TOKENS = 16


class LLMUnavailable(RuntimeError):
    """Raised when an LLM call cannot be made (no SDK, no key, cap reached)."""


class SpendStore(Protocol):
    """Persistence contract for token spend (implemented by CallDatabase)."""

    def month_to_date_spend(self, month: str) -> float: ...

    def record_llm_usage(self, entry: dict[str, Any]) -> None: ...


@dataclass
class UsageRecord:
    role: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: float
    web_searches: int = 0


@dataclass
class RunCost:
    """Accumulated token cost for one run."""

    records: list[UsageRecord] = field(default_factory=list)

    @property
    def total_usd(self) -> float:
        return round(sum(record.cost_usd for record in self.records), 6)

    @property
    def total_input_tokens(self) -> int:
        return sum(record.input_tokens for record in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(record.output_tokens for record in self.records)

    def summary(self) -> dict[str, Any]:
        per_model: dict[str, float] = {}
        for record in self.records:
            per_model[record.model] = round(per_model.get(record.model, 0.0) + record.cost_usd, 6)
        return {
            "calls": len(self.records),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "web_searches": sum(record.web_searches for record in self.records),
            "cost_usd": self.total_usd,
            "cost_by_model": per_model,
        }


def current_month(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


def extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object from *text* (tolerates fences and prose)."""
    if not text:
        raise ValueError("empty response")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [fenced.group(1)] if fenced else []
    depth = 0
    start = None
    for index, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : index + 1])
                start = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("no JSON object found in response")


class LLMClient:
    """Thin Messages API client with cost accounting."""

    def __init__(
        self,
        config: dict[str, Any],
        spend_store: SpendStore | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self.config = config
        self.spend_store = spend_store
        self.run_cost = RunCost()
        self._client = client
        self._unavailable_reason: str | None = None

        if client is None:
            if not HAS_ANTHROPIC:
                self._unavailable_reason = "the 'anthropic' package is not installed"
            elif not os.environ.get("ANTHROPIC_API_KEY"):
                self._unavailable_reason = "ANTHROPIC_API_KEY is not set"

    # ---------------------------------------------------------------- pricing

    def model_for(self, kind: str) -> str:
        models = self.config["roles"]["models"]
        return models.get(kind) or models["worker"]

    def price_usd(
        self, model: str, input_tokens: int, output_tokens: int, cached: int = 0
    ) -> float:
        prices = self.config["llm"].get("prices_per_mtok", {}).get(model)
        if not prices:
            return 0.0
        cost = (
            input_tokens * float(prices.get("input", 0.0))
            + output_tokens * float(prices.get("output", 0.0))
            + cached * float(prices.get("cache_read", 0.0))
        ) / 1_000_000
        return round(cost, 8)

    def month_to_date_spend(self, month: str | None = None) -> float:
        if not self.spend_store:
            return self.run_cost.total_usd
        return float(self.spend_store.month_to_date_spend(month or current_month()))

    def cap_usd(self) -> float:
        return float(self.config["llm"].get("monthly_spend_cap_usd", 0.0) or 0.0)

    def cap_remaining(self) -> float:
        cap = self.cap_usd()
        if cap <= 0:
            return float("inf")
        return round(cap - self.month_to_date_spend(), 6)

    # ------------------------------------------------------------ availability

    def availability(self) -> dict[str, Any]:
        if self._unavailable_reason:
            return {"available": False, "reason": self._unavailable_reason}
        remaining = self.cap_remaining()
        if remaining <= 0:
            return {
                "available": False,
                "reason": (
                    f"monthly LLM spend cap reached "
                    f"(${self.month_to_date_spend():.4f} of ${self.cap_usd():.2f})"
                ),
            }
        return {"available": True, "reason": "ok", "cap_remaining_usd": remaining}

    def available(self) -> bool:
        return bool(self.availability()["available"])

    # ------------------------------------------------------------------ calls

    def _sdk_client(self) -> Any:
        if self._client is None:
            if self._unavailable_reason:
                raise LLMUnavailable(self._unavailable_reason)
            self._client = anthropic.Anthropic()
        return self._client

    def web_search_tool(self) -> dict[str, Any]:
        """The server-side web search tool definition, from configuration."""
        search = self.config["roles"].get("web_search", {}) or {}
        tool: dict[str, Any] = {
            "type": str(search.get("tool_version", WEB_SEARCH_TOOL_VERSION)),
            "name": "web_search",
            "max_uses": int(search.get("max_uses", 5)),
        }
        allowed = search.get("allowed_domains")
        if allowed:
            tool["allowed_domains"] = list(allowed)
        return tool

    def search_price_usd(self, searches: int) -> float:
        """Server-side web searches are billed per search, not per token."""
        per_thousand = float(self.config["llm"].get("web_search_per_1k_searches") or 0.0)
        return round(searches * per_thousand / 1000.0, 8)

    def health_check(self, *, model_kind: str = "worker") -> dict[str, Any]:
        """Prove the backend answers, with the smallest call that can fail.

        Returns ``{"ok": bool, "reason": str, ...}``. Never raises: the caller
        decides what a dead backend means for the run.
        """
        started = datetime.now(timezone.utc)
        availability = self.availability()
        if not availability["available"]:
            return {
                "ok": False,
                "reason": availability["reason"],
                "stage": "availability",
                "model": self.model_for(model_kind),
            }
        model = self.model_for(model_kind)
        try:
            response = self._sdk_client().messages.create(
                model=model,
                max_tokens=HEALTH_CHECK_MAX_TOKENS,
                messages=[{"role": "user", "content": HEALTH_CHECK_PROMPT}],
            )
        except Exception as exc:
            return {
                "ok": False,
                "reason": f"{type(exc).__name__}: {exc}",
                "stage": "request",
                "model": model,
            }

        usage = getattr(response, "usage", None)
        record = UsageRecord(
            role="health_check",
            model=model,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            cost_usd=0.0,
        )
        record.cost_usd = self.price_usd(
            model, record.input_tokens, record.output_tokens, record.cache_read_tokens
        )
        self.run_cost.records.append(record)
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return {
            "ok": True,
            "reason": "ok",
            "stage": "complete",
            "model": model,
            "latency_ms": elapsed_ms,
            "cost_usd": record.cost_usd,
            "cap_remaining_usd": self.cap_remaining(),
        }

    def _extra_params(self, model: str, kind: str) -> dict[str, Any]:
        """Thinking / effort parameters the model actually accepts."""
        if model.startswith(_NO_THINKING_PREFIXES):
            return {}
        effort = "medium" if kind == "judge" else "low"
        return {"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}

    def complete_json(
        self,
        *,
        role: str,
        kind: str,
        system: str,
        user: str,
        web_search: bool = False,
    ) -> tuple[dict[str, Any], UsageRecord]:
        """Run one role prompt and return its parsed JSON verdict plus usage.

        With *web_search*, the model is given Anthropic's server-side search
        tool: it issues the searches, the API runs them, and the final text
        block carries the verdict. Searches are billed per search and added to
        this call's cost.
        """
        availability = self.availability()
        if not availability["available"]:
            raise LLMUnavailable(availability["reason"])

        model = self.model_for(kind)
        max_tokens = int(self.config["roles"].get("max_tokens", {}).get(kind, 1200))
        client = self._sdk_client()

        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            **self._extra_params(model, kind),
        }
        if web_search:
            params["tools"] = [self.web_search_tool()]

        try:
            response = client.messages.create(**params)
        except Exception as exc:  # SDK-specific errors surface as one failure mode
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc

        usage = getattr(response, "usage", None)
        searches = 0
        server_use = getattr(usage, "server_tool_use", None)
        if server_use is not None:
            searches = int(getattr(server_use, "web_search_requests", 0) or 0)
        record = UsageRecord(
            role=role,
            model=model,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
            cost_usd=0.0,
            web_searches=searches,
        )
        record.cost_usd = self.price_usd(
            model, record.input_tokens, record.output_tokens, record.cache_read_tokens
        ) + self.search_price_usd(searches)
        self.run_cost.records.append(record)

        if getattr(response, "stop_reason", None) == "refusal":
            raise LLMUnavailable(f"{model} declined the request")

        text = "".join(
            block.text
            for block in getattr(response, "content", [])
            if getattr(block, "type", None) == "text"
        )
        return extract_json(text), record

    def persist_run_cost(self, run_id: str, month: str | None = None) -> dict[str, Any]:
        """Write this run's usage records to the spend store; return the summary."""
        summary = self.run_cost.summary()
        if self.spend_store:
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for record in self.run_cost.records:
                self.spend_store.record_llm_usage(
                    {
                        "run_id": run_id,
                        "created_at": stamp,
                        "month": month or current_month(),
                        "role": record.role,
                        "model": record.model,
                        "input_tokens": record.input_tokens,
                        "output_tokens": record.output_tokens,
                        "cache_read_tokens": record.cache_read_tokens,
                        "cost_usd": record.cost_usd,
                    }
                )
        return summary
