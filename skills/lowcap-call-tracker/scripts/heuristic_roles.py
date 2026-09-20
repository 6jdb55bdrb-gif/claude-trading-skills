#!/usr/bin/env python3
"""Deterministic (offline) implementation of the five review roles.

This backend exists for three reasons: tests and dry runs must not need network
or an API key, a run must survive an exhausted monthly LLM budget, and the LLM
backend needs a reference shape for every verdict. It produces the same JSON
contract as the ``agents/lowcap-*.md`` prompts.

Polarity reminder: ``skeptic.score`` is OBJECTION SEVERITY — 0 means nothing
found, 10 means disqualifying.
"""

from __future__ import annotations

from typing import Any

CATALYST_TYPES = {
    "earnings",
    "guidance",
    "fda_regulatory",
    "contract_award",
    "ma",
    "analyst_action",
    "product_launch",
    "sector_theme",
    "insider_buying",
    "short_squeeze_mechanics",
    "retail_hype",
    "none_found",
}

# stockbee-episodic-pivot-analyzer catalyst_type -> our enum.
_EP_CATALYST_MAP = {
    "earnings": "earnings",
    "earnings_beat": "earnings",
    "guidance_raise": "guidance",
    "guidance": "guidance",
    "fda_approval": "fda_regulatory",
    "regulatory": "fda_regulatory",
    "major_contract": "contract_award",
    "contract": "contract_award",
    "ma": "ma",
    "merger_acquisition": "ma",
    "analyst_action": "analyst_action",
    "product_launch": "product_launch",
    "theme": "sector_theme",
    "story": "sector_theme",
    "short_squeeze": "short_squeeze_mechanics",
}

LEVERAGED_MARKERS = ("2X", "3X", "ULTRA", "BULL", "BEAR", "LEVERAGED", "INVERSE", "SHORT")


def clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except ValueError:
        return None


def dollar_volume(hit: dict[str, Any]) -> float | None:
    price = _num(hit.get("price"))
    volume = _num(hit.get("avg_volume")) or _num(hit.get("volume"))
    if price is None or volume is None:
        return None
    return price * volume


def is_leveraged_etf(hit: dict[str, Any]) -> bool:
    if hit.get("asset_type") != "etf":
        return False
    haystack = f"{hit.get('ticker', '')} {hit.get('company', '')}".upper()
    return any(marker in haystack for marker in LEVERAGED_MARKERS)


# ------------------------------------------------------------- RESEARCHER


def researcher(hit: dict[str, Any], *, episodic_pivot: dict[str, Any] | None = None) -> dict:
    headline = hit.get("catalyst_headline") or hit.get("headline")
    reasons: list[str] = []
    catalyst_type = "none_found"
    score = 2.0

    ep_score = _num((episodic_pivot or {}).get("composite_score"))
    if episodic_pivot and ep_score is not None:
        raw_type = str(episodic_pivot.get("catalyst_type") or "").lower()
        catalyst_type = _EP_CATALYST_MAP.get(
            raw_type, raw_type if raw_type in CATALYST_TYPES else "sector_theme"
        )
        score = clamp(ep_score / 10.0)
        reasons.append(
            f"episodic-pivot analyzer: {episodic_pivot.get('ep_type', 'EP')} "
            f"score {ep_score:.0f} rating {episodic_pivot.get('rating', '?')}"
        )
        if catalyst_type in {"none_found", "sector_theme"} and not headline:
            score = min(score, 4.0)
            reasons.append("catalyst type not identifiable from the event record")
    elif headline:
        catalyst_type = "sector_theme"
        score = 4.0
        reasons.append("headline supplied but not classified by the episodic-pivot analyzer")
    else:
        reasons.append("no catalyst found: move is unexplained by any supplied event")

    if hit.get("asset_type") == "etf":
        # An ETF's catalyst is its basket's theme; a bare price move is not one.
        theme = hit.get("theme") or hit.get("industry")
        if theme and catalyst_type == "none_found":
            catalyst_type = "sector_theme"
            score = max(score, 4.0)
            reasons.append(f"ETF thematic driver: {theme}")
        else:
            reasons.append("ETF: score reflects theme durability, not company news")

    relvol = _num(hit.get("rel_volume"))
    if relvol and relvol >= 3 and score >= 4:
        score = clamp(score + 0.5)
        reasons.append(f"relative volume {relvol:.1f}x corroborates a real event")

    return {
        "role": "researcher",
        "score": round(score, 1),
        "catalyst_type": catalyst_type,
        "catalyst_summary": headline or "No catalyst identified from available data.",
        "catalyst_date": (episodic_pivot or {}).get("event_date") or hit.get("screened_at"),
        "sector_theme": hit.get("theme") or hit.get("industry"),
        "insider_buying": (_num(hit.get("insider_trans_pct")) or 0.0) > 0,
        "evidence": [headline] if headline else [],
        "reasons": reasons[:3],
        "backend": "heuristic",
    }


# -------------------------------------------------------------- TECHNICIAN


def technician(hit: dict[str, Any], *, weekly: dict[str, Any] | None = None) -> dict:
    price = _num(hit.get("price"))
    ext20 = _num(hit.get("sma20_pct"))
    ext50 = _num(hit.get("sma50_pct"))
    ext200 = _num(hit.get("sma200_pct"))
    relvol = _num(hit.get("rel_volume"))
    from_high = _num(hit.get("high52w_pct"))
    rsi = _num(hit.get("rsi"))
    reasons: list[str] = []

    score = 5.0
    trend = "range"
    if ext20 is not None and ext20 > 0 and ext50 is not None and ext50 > 0:
        trend = "uptrend"
        score += 1.0
        reasons.append("price above both SMA20 and SMA50")
    elif ext20 is not None and ext20 > 0:
        trend = "bounce"
        reasons.append("above SMA20 but not SMA50: bounce, not trend")
    elif ext20 is not None:
        trend = "downtrend"
        score -= 2.0
        reasons.append("price below SMA20")
    if ext200 is not None and ext200 > 0:
        score += 0.5

    if relvol is not None:
        if relvol >= 8:
            score -= 2.0
            volume_pattern = "climactic"
            reasons.append(f"relative volume {relvol:.1f}x is blow-off territory")
        elif relvol >= 2:
            score += 1.0
            volume_pattern = "confirming"
            reasons.append(f"relative volume {relvol:.1f}x confirms the move")
        else:
            volume_pattern = "fading"
            reasons.append(f"relative volume {relvol:.1f}x does not confirm")
    else:
        volume_pattern = "thin"

    if ext20 is not None:
        if ext20 > 40:
            score -= 2.5
            reasons.append(f"{ext20:.0f}% above SMA20: entry risk is high")
        elif ext20 > 20:
            score -= 1.0
            reasons.append(f"{ext20:.0f}% above SMA20: extended")
    if rsi is not None and rsi >= 85:
        score -= 1.0
        reasons.append(f"RSI {rsi:.0f} overbought")

    breakout_quality = "not_a_breakout"
    if from_high is not None and from_high >= -2:
        breakout_quality = "high" if (relvol or 0) >= 2 and (ext20 or 0) <= 25 else "low"
        score += 1.0 if breakout_quality == "high" else 0.0
        reasons.append("at or within 2% of the 52-week high")

    support = resistance = None
    if weekly and weekly.get("swing_levels"):
        levels = weekly["swing_levels"]
        support = _num(levels.get("support") or levels.get("swing_low"))
        resistance = _num(levels.get("resistance") or levels.get("swing_high"))
        verdict = weekly.get("verdict")
        if verdict and verdict != "INSUFFICIENT_DATA":
            reasons.append(f"weekly price action: {verdict}")
            if "FAIL" in str(verdict).upper():
                score -= 1.0
    if support is None and price and ext20 is not None:
        support = round(price / (1 + ext20 / 100.0), 2)  # the SMA20 level
    if resistance is None and price and from_high is not None:
        resistance = round(price / (1 + from_high / 100.0), 2)  # the 52-week high

    if not weekly or weekly.get("verdict") in {None, "INSUFFICIENT_DATA"}:
        score = min(score, 6.0)
        reasons.append("no weekly price history: scored from screener fields only (cap 6)")

    return {
        "role": "technician",
        "score": round(clamp(score), 1),
        "trend": trend,
        "support": support,
        "resistance": resistance,
        "volume_pattern": volume_pattern,
        "extension_pct_sma20": ext20,
        "breakout_quality": breakout_quality,
        "reasons": reasons[:3],
        "backend": "heuristic",
    }


# ------------------------------------------------------------------ SKEPTIC


def skeptic(
    hit: dict[str, Any],
    *,
    researcher_verdict: dict[str, Any] | None = None,
    technician_verdict: dict[str, Any] | None = None,
) -> dict:
    severity = 3.0  # baseline: this universe dilutes and fades by default
    flags: list[str] = []
    contributions: list[tuple[float, str, str]] = []
    price = _num(hit.get("price"))
    ext20 = _num((technician_verdict or {}).get("extension_pct_sma20")) or _num(
        hit.get("sma20_pct")
    )
    relvol = _num(hit.get("rel_volume"))
    dollars = dollar_volume(hit)
    short_float = _num(hit.get("short_float_pct"))
    is_etf = hit.get("asset_type") == "etf"

    if ext20 is not None and ext20 > 40:
        contributions.append(
            (3.0, "extension", f"{ext20:.0f}% above SMA20 — the move has already paid")
        )
    elif ext20 is not None and ext20 > 20:
        contributions.append((1.5, "extension", f"{ext20:.0f}% above SMA20 — late entry risk"))
    if relvol is not None and relvol >= 8:
        contributions.append((2.0, "extension", f"relative volume {relvol:.1f}x looks climactic"))
    if dollars is not None and dollars < 2_000_000:
        contributions.append(
            (2.0, "liquidity", f"only ${dollars / 1e6:.1f}M average dollar volume to exit into")
        )

    researcher_score = _num((researcher_verdict or {}).get("score"))
    if researcher_score is not None and researcher_score <= 3:
        contributions.append(
            (
                2.5,
                "pump_and_dump",
                "no identifiable catalyst — an unexplained move in this universe is usually supply",
            )
        )

    if is_etf:
        if is_leveraged_etf(hit):
            contributions.append(
                (
                    2.0,
                    "etf_mechanics",
                    "leveraged/inverse structure: daily reset decays a multi-week hold",
                )
            )
        if dollars is not None and dollars < 5_000_000:
            contributions.append(
                (
                    1.5,
                    "etf_mechanics",
                    "thin ETF: spread and premium/discount to NAV dominate slippage",
                )
            )
    else:
        if price is not None and price < 1.5:
            contributions.append(
                (2.5, "dilution", f"${price:.2f} share price is prime ATM/shelf-offering territory")
            )
        if short_float is not None and short_float >= 30:
            contributions.append(
                (
                    1.5,
                    "short_thesis_correct",
                    f"{short_float:.0f}% short float may be a correct thesis, not fuel",
                )
            )
        if hit.get("reverse_split_recent"):
            contributions.append(
                (2.0, "structure", "recent reverse split resets the per-share picture")
            )

    for weight, _category, text in contributions:
        severity += weight
        flags.append(text)

    if contributions:
        category = max(contributions, key=lambda item: item[0])[1]
        strongest = max(contributions, key=lambda item: item[0])[2]
    else:
        category = "none"
        strongest = "No specific disqualifier found in the available data."
        severity = min(severity, 2.0)

    change = _num(hit.get("change_pct"))
    what_would_change = (
        "A filed prospectus showing the ATM is exhausted, or a closed raise that removes the overhang."
        if category == "dilution"
        else "A named, dated primary source for the move plus a held close above today's high."
        if category == "pump_and_dump"
        else "A pullback to within 10% of the SMA20 that holds on declining volume."
        if category == "extension"
        else f"Average dollar volume above $5M sustained for a week (today: {change or 0:+.1f}%)."
    )

    return {
        "role": "skeptic",
        "score": round(clamp(severity), 1),
        "strongest_objection": strongest,
        "objection_category": category,
        "risk_flags": flags[:4],
        "what_would_change_my_mind": what_would_change,
        "reasons": flags[:3] or ["no specific objection evidenced by the available fields"],
        "backend": "heuristic",
        "score_polarity": "severity: 0 = no objection, 10 = disqualifying",
    }


# ------------------------------------------------------------- RISK MANAGER


def risk_manager(
    hit: dict[str, Any],
    *,
    technician_verdict: dict[str, Any] | None = None,
    skeptic_verdict: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    sizing: dict[str, Any] | None = None,
) -> dict:
    price = _num(hit.get("price"))
    atr = _num(hit.get("atr"))
    tech = technician_verdict or {}
    skeptic_score = _num((skeptic_verdict or {}).get("score")) or 0.0
    ext20 = _num(tech.get("extension_pct_sma20"))
    reasons: list[str] = []

    if price is None or price <= 0:
        return {
            "role": "risk_manager",
            "score": 0.0,
            "direction": "none",
            "direction_reason": "no usable price",
            "entry": None,
            "stop": None,
            "stop_basis": None,
            "target": None,
            "r_multiple_to_target": None,
            "shares": None,
            "position_usd": None,
            "risk_usd": None,
            "position_pct_of_account": None,
            "reasons": ["screener row carries no price"],
            "backend": "heuristic",
        }

    short_case = (
        tech.get("trend") == "downtrend"
        or (ext20 is not None and ext20 > 50 and skeptic_score >= 7)
        or (tech.get("volume_pattern") == "climactic" and skeptic_score >= 8)
    )
    direction = "short" if short_case else "long"
    direction_reason = (
        "climactic extension plus a severe objection: the edge is in the fade"
        if short_case
        else "every variant screens for strength; default long"
    )

    support = _num(tech.get("support"))
    resistance = _num(tech.get("resistance"))
    stop_basis = "percent"
    if direction == "long":
        stop = support if support and 0 < support < price else None
        if stop:
            stop_basis = "structure"
        elif atr:
            stop, stop_basis = price - 1.8 * atr, "atr"
        else:
            stop = price * 0.85
        stop = max(stop, price * 0.80)  # cap risk at 20% of price
    else:
        stop = resistance if resistance and resistance > price else None
        if stop:
            stop_basis = "structure"
        elif atr:
            stop, stop_basis = price + 1.8 * atr, "atr"
        else:
            stop = price * 1.15
        stop = min(stop, price * 1.20)

    stop = round(stop, 2)
    risk_per_share = abs(price - stop)
    if risk_per_share <= 0:
        return {
            "role": "risk_manager",
            "score": 1.0,
            "direction": "none",
            "direction_reason": "stop collapses onto the entry",
            "entry": price,
            "stop": stop,
            "stop_basis": stop_basis,
            "target": None,
            "r_multiple_to_target": None,
            "shares": None,
            "position_usd": None,
            "risk_usd": None,
            "position_pct_of_account": None,
            "reasons": ["no tradable stop distance"],
            "backend": "heuristic",
        }

    stop_pct = risk_per_share / price * 100
    target = (
        round(price + 2 * risk_per_share, 2)
        if direction == "long"
        else round(price - 2 * risk_per_share, 2)
    )

    tracker = (config or {}).get("tracker", {})
    account = _num(tracker.get("account_size")) or 10000.0
    risk_pct = _num(tracker.get("risk_pct")) or 1.0
    if sizing and sizing.get("shares"):
        shares = sizing["shares"]
        position_usd = sizing.get("position_usd")
        risk_usd = sizing.get("risk_usd")
        reasons.append("sized by the position-sizer skill")
        if sizing.get("binding_constraint"):
            reasons.append(f"binding constraint: {sizing['binding_constraint']}")
    else:
        risk_usd = account * risk_pct / 100.0
        shares = int(risk_usd // risk_per_share)
        position_usd = round(shares * price, 2)
    position_pct = round((position_usd or 0) / account * 100, 2) if account else None

    score = 5.0
    if stop_basis == "structure":
        score += 2.0
        reasons.append(f"structural stop at {stop} ({stop_pct:.1f}% away)")
    else:
        reasons.append(f"{stop_basis} stop at {stop} ({stop_pct:.1f}% away)")
    if stop_pct <= 12:
        score += 1.0
    elif stop_pct > 18:
        score -= 2.0
        reasons.append("stop distance above 18% of price: size becomes uneconomic")
    dollars = dollar_volume(hit)
    if dollars and position_usd and position_usd > dollars * 0.01:
        score -= 1.5
        reasons.append("position is over 1% of average dollar volume: exit slippage risk")
    elif dollars and dollars > 10_000_000:
        score += 0.5
    if not shares:
        score = min(score, 3.0)
        reasons.append("risk budget rounds to zero shares")

    return {
        "role": "risk_manager",
        "score": round(clamp(score), 1),
        "direction": direction if shares else "none",
        "direction_reason": direction_reason,
        "entry": round(price, 4),
        "stop": stop,
        "stop_basis": stop_basis,
        "target": target,
        "r_multiple_to_target": 2.0,
        "shares": shares,
        "position_usd": position_usd,
        "risk_usd": round(risk_usd, 2) if risk_usd else None,
        "position_pct_of_account": position_pct,
        "reasons": reasons[:3],
        "backend": "heuristic",
    }


# -------------------------------------------------------------------- JUDGE


def weighted_score(verdicts: dict[str, dict[str, Any]], weights: dict[str, float]) -> float:
    """Blend the four role scores; the Skeptic's severity is subtracted."""
    positive = sum(
        float(weights.get(role, 1.0)) * float(verdicts.get(role, {}).get("score") or 0.0)
        for role in ("researcher", "technician", "risk_manager")
    )
    penalty = float(weights.get("skeptic", 1.0)) * float(
        verdicts.get("skeptic", {}).get("score") or 0.0
    )
    return positive - penalty


def confidence_from_scores(verdicts: dict[str, dict[str, Any]], weights: dict[str, float]) -> int:
    raw = weighted_score(verdicts, weights)
    best = 10.0 * sum(
        float(weights.get(role, 1.0)) for role in ("researcher", "technician", "risk_manager")
    )
    worst = -10.0 * float(weights.get("skeptic", 1.0))
    span = best - worst or 1.0
    return int(round(clamp((raw - worst) / span * 100, 0, 100)))


def judge(verdicts: dict[str, dict[str, Any]], *, config: dict[str, Any]) -> dict:
    weights = config["roles"].get("weights", {})
    judge_cfg = config["roles"].get("judge", {})
    minimum = int(judge_cfg.get("min_confidence_to_take", 55))

    researcher_v = verdicts.get("researcher", {})
    technician_v = verdicts.get("technician", {})
    skeptic_v = verdicts.get("skeptic", {})
    risk_v = verdicts.get("risk_manager", {})

    confidence = confidence_from_scores(verdicts, weights)
    severity = float(skeptic_v.get("score") or 0.0)
    category = skeptic_v.get("objection_category", "none")
    objection = skeptic_v.get("strongest_objection", "none stated")

    answered = False
    answer = f"Objection stands unanswered: {objection}"
    if severity <= 2:
        answered = True
        answer = "Skeptic found nothing disqualifying, so there is nothing to rebut."
    elif severity < 8:
        if (
            float(researcher_v.get("score") or 0) >= 6
            and float(technician_v.get("score") or 0) >= 6
        ):
            answered = True
            answer = (
                f"'{objection}' is offset by a dated catalyst (researcher "
                f"{researcher_v.get('score')}) and confirming structure (technician "
                f"{technician_v.get('score')}); the {risk_v.get('stop_basis')} stop at "
                f"{risk_v.get('stop')} caps the loss if it is right."
            )
    elif (
        category not in {"dilution", "pump_and_dump"} and float(researcher_v.get("score") or 0) >= 8
    ):
        answered = True
        answer = (
            f"Severe objection '{objection}' is outweighed by a hard catalyst "
            f"(researcher {researcher_v.get('score')}); risk is bounded by the stop."
        )

    reasons = [
        f"researcher {researcher_v.get('score')} / technician {technician_v.get('score')} "
        f"/ risk {risk_v.get('score')} vs skeptic severity {severity}",
        f"weighted confidence {confidence}",
        answer,
    ]

    decision = "TAKE"
    if risk_v.get("direction") in {None, "none"}:
        decision, reason = "SKIP", "no executable plan: Risk Manager returned no direction"
    elif judge_cfg.get("require_skeptic_answer", True) and not answered:
        decision, reason = "SKIP", f"Skeptic objection unanswered ({category})"
    elif confidence < minimum:
        decision, reason = "SKIP", f"confidence {confidence} below the {minimum} threshold"
    else:
        reason = (
            f"{researcher_v.get('catalyst_type')} catalyst with "
            f"{technician_v.get('trend')} structure; objection answered"
        )

    return {
        "role": "judge",
        "decision": decision,
        "confidence": confidence,
        "reason": reason[:140],
        "skeptic_objections_answered": answered,
        "skeptic_answer": answer,
        "key_risk": objection,
        "reasons": reasons[:3],
        "backend": "heuristic",
    }
