#!/usr/bin/env python3
"""The v2 explosion-signals layer: what makes a lowcap move, scored.

Runs on every surviving hit after the FinViz filters and before the Judge, so
the five roles argue with the numbers in front of them instead of around them.
v1 has no signals layer and is not touched by any of this.

Two rules run through the whole module:

* **A source that failed is not evidence.** Each signal reports ``ok`` (it
  looked, here is what it found) or ``n/a`` (it could not look). An ``n/a``
  scores nothing. Collapsing the two would make "EDGAR was unreachable"
  indistinguishable from "the company has filed nothing", and those lead to
  opposite decisions.
* **Signals rank setups; they do not manufacture them.** Hence
  ``max_total_bonus``, which caps what the layer may add, and the hard skips,
  which no amount of bonus can outvote.

Scoring here is pure: facts the screener row already carries are derived
directly, and everything needing a network call arrives in *data*, gathered by
``signal_providers``. That split is what lets the whole layer be tested
offline and keeps a provider outage from ever reaching the Judge as a number.
"""

from __future__ import annotations

from typing import Any

from screener_guards import hit_version
from screener_variants import version_block

SIGNAL_ORDER = (
    "float_rotation",
    "catalyst_recency",
    "short_squeeze_pressure",
    "volatility_contraction",
    "premarket_gap",
    "vwap_position",
    "insider_buying",
    "institutional_ownership",
    "sector_sympathy",
)

HARD_SKIP_ORDER = ("dilution_filings", "reverse_split", "cash_runway", "intraday_halts")

# Short labels for the Telegram line and the role prompts.
SIGNAL_LABELS = {
    "float_rotation": "float rotation",
    "catalyst_recency": "catalyst",
    "short_squeeze_pressure": "squeeze pressure",
    "volatility_contraction": "coiled range",
    "premarket_gap": "premarket gap",
    "vwap_position": "VWAP",
    "insider_buying": "insider buy",
    "institutional_ownership": "thin institutions",
    "sector_sympathy": "sector sympathy",
}


def _number(value: Any) -> float | None:
    """Parse a cell into a finite float, or None. Never raises."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("%", "").replace(",", "").replace("+", "")
        if not text or text in {"-", "--", "n/a", "N/A", "none", "None"}:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    if number != number:  # NaN
        return None
    return number


def signals_config(config: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    """The explosion-signals block for a version, or ``{}`` when it has none."""
    try:
        return version_block(config, version).get("explosion_signals") or {}
    except Exception:  # pragma: no cover - unknown version is caught upstream
        return {}


def signals_enabled(config: dict[str, Any], version: str | None = None) -> bool:
    block = signals_config(config, version)
    return bool(block) and bool(block.get("enabled", True))


def edgar_settings(config: dict[str, Any], version: str | None = None) -> dict[str, Any]:
    return signals_config(config, version).get("edgar") or {}


def _spec(block: dict[str, Any], name: str) -> dict[str, Any]:
    return (block.get("signals") or {}).get(name) or {}


def _skip_spec(block: dict[str, Any], name: str) -> dict[str, Any]:
    return (block.get("hard_skips") or {}).get(name) or {}


def _entry(status: str, *, value: Any = None, points: int = 0, detail: str = "") -> dict[str, Any]:
    return {"status": status, "value": value, "points": int(points), "detail": detail}


_NA = "n/a"
_OK = "ok"


# --- the nine signals ----------------------------------------------------


def _float_rotation(hit: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Today's volume over the free float: how much of the supply changed hands."""
    volume = _number(hit.get("volume"))
    float_shares = _number(hit.get("float_shares"))
    if volume is None or not float_shares or float_shares <= 0:
        return _entry(_NA, detail="no float or volume on the screener row")
    rotation = round(volume / float_shares, 2)
    for rung in sorted(
        spec.get("rungs") or [], key=lambda r: _number(r.get("min_x")) or 0.0, reverse=True
    ):
        threshold = _number(rung.get("min_x"))
        if threshold is not None and rotation >= threshold:
            return _entry(
                _OK,
                value=rotation,
                points=int(_number(rung.get("points")) or 0),
                detail=f"{rotation:.2f}x float rotation",
            )
    return _entry(_OK, value=rotation, detail=f"{rotation:.2f}x float rotation")


def _catalyst_recency(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """A material filing or news item inside the window.

    In v2 this replaces the role-level ``no_catalyst_penalty``: the charge is
    made once, here, against the filing and news record rather than against a
    role's opinion of it.
    """
    window = _number(spec.get("window_hours")) or 24.0
    reward = int(_number(spec.get("points")) or 0)
    penalty = int(_number(spec.get("no_catalyst_penalty")) or 0)

    filing_age = _number(data.get("catalyst_hours_ago"))
    news_age = _number(data.get("news_hours_ago"))
    ages = [age for age in (filing_age, news_age) if age is not None]
    if ages:
        freshest = min(ages)
        source = data.get("catalyst_form") if freshest == filing_age else "news"
        if freshest <= window:
            return _entry(
                _OK,
                value=round(freshest, 1),
                points=reward,
                detail=f"{source or 'filing'} {freshest:.0f}h ago",
            )
        return _entry(
            _OK,
            value=round(freshest, 1),
            points=-penalty,
            detail=f"nothing inside {window:.0f}h (last {source or 'filing'} {freshest:.0f}h ago)",
        )

    # Nothing dated. "Looked and found nothing" is charged; "could not look"
    # is not. The provider says which by setting catalyst_found.
    found = data.get("catalyst_found")
    if found is False:
        return _entry(_OK, value=None, points=-penalty, detail="no filing or news found")
    return _entry(_NA, detail="filing and news record unavailable")


def _short_squeeze_pressure(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Days to cover, or a punitive borrow fee — the same fact from two sides."""
    days_to_cover = _number(hit.get("short_ratio"))
    borrow_fee = _number(data.get("borrow_fee_pct"))
    if days_to_cover is None and borrow_fee is None:
        return _entry(_NA, detail="no short ratio and no borrow data")

    min_days = _number(spec.get("min_days_to_cover"))
    min_fee = _number(spec.get("min_borrow_fee_pct"))
    reasons = []
    if days_to_cover is not None and min_days is not None and days_to_cover >= min_days:
        reasons.append(f"{days_to_cover:.1f} days to cover")
    if borrow_fee is not None and min_fee is not None and borrow_fee >= min_fee:
        reasons.append(f"{borrow_fee:.0f}% borrow fee")
    value = {"days_to_cover": days_to_cover, "borrow_fee_pct": borrow_fee}
    if reasons:
        # "and/or": either side pays, and both together still pay once.
        return _entry(
            _OK,
            value=value,
            points=int(_number(spec.get("points")) or 0),
            detail=", ".join(reasons),
        )
    return _entry(_OK, value=value, detail="no squeeze pressure")


def _volatility_contraction(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """A range in the bottom fifth of its own history, with volume arriving."""
    percentile = _number(data.get("range_percentile"))
    if percentile is None:
        return _entry(_NA, detail="no price history for the range percentile")
    rel_volume = _number(hit.get("rel_volume"))
    ceiling = _number(spec.get("percentile")) or 20.0
    min_rel = _number(spec.get("min_rel_volume")) or 2.0
    coiled = percentile <= ceiling
    volume_in = rel_volume is not None and rel_volume >= min_rel
    if coiled and volume_in:
        return _entry(
            _OK,
            value=round(percentile, 1),
            points=int(_number(spec.get("points")) or 0),
            detail=f"range in the {percentile:.0f}th percentile on {rel_volume:.1f}x volume",
        )
    if coiled:
        # Contraction on its own is just a quiet stock.
        return _entry(_OK, value=round(percentile, 1), detail="coiled, but volume has not arrived")
    return _entry(
        _OK, value=round(percentile, 1), detail=f"range in the {percentile:.0f}th percentile"
    )


def _premarket_gap(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """A gap that real premarket volume paid for."""
    gap = _number(data.get("premarket_gap_pct"))
    volume_pct = _number(data.get("premarket_volume_pct_of_adv"))
    if gap is None:
        return _entry(_NA, detail="no premarket session data")
    min_gap = _number(spec.get("min_gap_pct")) or 10.0
    min_volume = _number(spec.get("min_volume_pct_of_adv")) or 20.0
    value = {"gap_pct": round(gap, 1), "volume_pct_of_adv": volume_pct}
    if gap >= min_gap and volume_pct is not None and volume_pct >= min_volume:
        return _entry(
            _OK,
            value=value,
            points=int(_number(spec.get("points")) or 0),
            detail=f"gapped {gap:+.1f}% on {volume_pct:.0f}% of ADV premarket",
        )
    if gap >= min_gap:
        # A big print on no volume is one order, not demand.
        return _entry(_OK, value=value, detail=f"gapped {gap:+.1f}% on thin premarket volume")
    return _entry(_OK, value=value, detail=f"premarket gap {gap:+.1f}%")


def _vwap_position(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Above or below the day's volume-weighted average price.

    The only signal that is negative on its own. Under VWAP every buyer from
    today is underwater, and that is where the supply in a failed run comes
    from.
    """
    vwap = _number(data.get("vwap"))
    price = _number(hit.get("price"))
    if vwap is None or price is None:
        return _entry(_NA, detail="no intraday VWAP")
    above = price >= vwap
    points = _number(spec.get("above_points" if above else "below_points")) or 0
    return _entry(
        _OK,
        value={"price": price, "vwap": round(vwap, 4)},
        points=int(points),
        detail=f"{'above' if above else 'below'} VWAP ({price:.2f} vs {vwap:.2f})",
    )


def _insider_buying(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """A Form 4 open-market purchase inside the window."""
    days_ago = _number(data.get("insider_buy_days_ago"))
    window = _number(spec.get("window_days")) or 30.0
    if days_ago is None:
        if data.get("insider_checked"):
            return _entry(_OK, detail="no open-market purchase on file")
        return _entry(_NA, detail="Form 4 record unavailable")
    if days_ago <= window:
        return _entry(
            _OK,
            value=int(days_ago),
            points=int(_number(spec.get("points")) or 0),
            detail=f"insider bought {days_ago:.0f} days ago",
        )
    return _entry(_OK, value=int(days_ago), detail=f"last purchase {days_ago:.0f} days ago")


def _institutional_ownership(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Thin institutional ownership: room for the move to be bought into."""
    owned = _number(hit.get("inst_own_pct"))
    if owned is None:
        return _entry(_NA, detail="no ownership data on the screener row")
    ceiling = _number(spec.get("max_pct")) or 20.0
    if owned < ceiling:
        return _entry(
            _OK,
            value=owned,
            points=int(_number(spec.get("points")) or 0),
            detail=f"{owned:.1f}% institutional",
        )
    return _entry(_OK, value=owned, detail=f"{owned:.1f}% institutional")


def _sector_sympathy(
    hit: dict[str, Any], spec: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Other names in the same industry running today — a theme, not a one-off."""
    peers = _number(data.get("sector_peers_up"))
    if peers is None:
        return _entry(_NA, detail="no peer scan")
    minimum = _number(spec.get("min_peers")) or 2.0
    threshold = _number(spec.get("peer_min_change_pct")) or 10.0
    detail = (
        f"{peers:.0f} peers up over {threshold:.0f}% in {hit.get('industry') or 'the industry'}"
    )
    if peers >= minimum:
        return _entry(
            _OK, value=int(peers), points=int(_number(spec.get("points")) or 0), detail=detail
        )
    return _entry(_OK, value=int(peers), detail=detail)


# --- the four hard skips -------------------------------------------------


def _dilution_filings(spec: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    filings = data.get("dilution_filings")
    if filings is None:
        return _entry(_NA, detail="EDGAR filing index unavailable")
    window = _number(spec.get("window_days")) or 90.0
    recent = [
        filing
        for filing in filings
        if (_number(filing.get("days_ago")) is not None)
        and _number(filing.get("days_ago")) <= window
    ]
    if not recent:
        return _entry(_OK, value=0, detail=f"no dilution filing in {window:.0f} days")
    worst = min(recent, key=lambda filing: _number(filing.get("days_ago")) or 0.0)
    return _entry(
        _OK,
        value=len(recent),
        points=0,
        detail=(
            f"{worst.get('form')} filed {_number(worst.get('days_ago')):.0f} days ago"
            + (f" (+{len(recent) - 1} more)" if len(recent) > 1 else "")
        ),
    ) | {"skip": True}


def _reverse_split(spec: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    days_ago = _number(data.get("reverse_split_days_ago"))
    if days_ago is None:
        return _entry(_NA, detail="split history unavailable")
    window = _number(spec.get("window_days")) or 180.0
    entry = _entry(_OK, value=int(days_ago), detail=f"reverse split {days_ago:.0f} days ago")
    return entry | {"skip": days_ago <= window}


def _cash_runway(spec: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    months = _number(data.get("cash_runway_months"))
    if months is None:
        return _entry(_NA, detail="no 10-Q cash or burn figures")
    minimum = _number(spec.get("min_months")) or 6.0
    if months == float("inf"):
        # No burn means no runway to run out of.
        return _entry(_OK, value=None, detail="no operating cash burn")
    entry = _entry(_OK, value=round(months, 1), detail=f"{months:.1f} months of cash")
    return entry | {"skip": months < minimum}


def _intraday_halts(spec: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    halts = _number(data.get("halts_today"))
    if halts is None:
        return _entry(_NA, detail="halt feed unavailable")
    ceiling = _number(spec.get("max_halts"))
    ceiling = 2.0 if ceiling is None else ceiling
    entry = _entry(_OK, value=int(halts), detail=f"{halts:.0f} halts today")
    return entry | {"skip": halts > ceiling}


_HARD_SKIP_REASONS = {
    "dilution_filings": "dilution risk",
    "reverse_split": "reverse split",
    "cash_runway": "cash runway",
    "intraday_halts": "repeated halts",
}


def evaluate(
    hit: dict[str, Any], config: dict[str, Any], *, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Score one hit. *data* carries everything that needed a network call."""
    version = hit_version(hit, config)
    block = signals_config(config, version)
    blank = {
        "enabled": False,
        "version": version,
        "bonus": 0,
        "raw_bonus": 0,
        "capped": False,
        "signals": {},
        "hard_skips": [],
        "hard_skip": False,
        "hard_skip_checks": {},
    }
    if not block or not block.get("enabled", True):
        return blank

    facts = data or {}
    signals: dict[str, Any] = {}
    for name in SIGNAL_ORDER:
        spec = _spec(block, name)
        if not spec.get("enabled", True):
            continue
        if name == "float_rotation":
            signals[name] = _float_rotation(hit, spec)
        elif name == "catalyst_recency":
            signals[name] = _catalyst_recency(hit, spec, facts)
        elif name == "short_squeeze_pressure":
            signals[name] = _short_squeeze_pressure(hit, spec, facts)
        elif name == "volatility_contraction":
            signals[name] = _volatility_contraction(hit, spec, facts)
        elif name == "premarket_gap":
            signals[name] = _premarket_gap(hit, spec, facts)
        elif name == "vwap_position":
            signals[name] = _vwap_position(hit, spec, facts)
        elif name == "insider_buying":
            signals[name] = _insider_buying(hit, spec, facts)
        elif name == "institutional_ownership":
            signals[name] = _institutional_ownership(hit, spec, facts)
        elif name == "sector_sympathy":
            signals[name] = _sector_sympathy(hit, spec, facts)

    checks: dict[str, Any] = {}
    reasons: list[str] = []
    for name in HARD_SKIP_ORDER:
        spec = _skip_spec(block, name)
        if not spec.get("enabled", True):
            continue
        if name == "dilution_filings":
            check = _dilution_filings(spec, facts)
        elif name == "reverse_split":
            check = _reverse_split(spec, facts)
        elif name == "cash_runway":
            check = _cash_runway(spec, facts)
        else:
            check = _intraday_halts(spec, facts)
        checks[name] = check
        if check.get("skip"):
            reasons.append(f"{_HARD_SKIP_REASONS[name]}: {check['detail']}")

    # The cap is on the layer's NET effect, and only on the upside: every
    # signal firing at once is +58, which would carry a 20-confidence setup
    # over any threshold. There is deliberately no floor — the VWAP charge and
    # the missing-catalyst charge are the layer's whole point on a weak sheet,
    # and a signal sheet is allowed to argue a name down as far as it likes.
    raw = sum(entry["points"] for entry in signals.values())
    ceiling = _number(block.get("max_total_bonus"))
    total = min(raw, ceiling) if ceiling is not None else raw
    return {
        "enabled": True,
        "version": version,
        "bonus": int(total),
        "raw_bonus": int(raw),
        "capped": bool(ceiling is not None and raw > ceiling),
        "signals": signals,
        "hard_skips": reasons,
        "hard_skip": bool(reasons),
        "hard_skip_checks": checks,
    }


def signal_summary(result: dict[str, Any], *, scored_only: bool = True) -> str:
    """One line for a role prompt, the run report or the Telegram message."""
    if not result.get("enabled"):
        return ""
    parts = []
    for name, entry in result.get("signals", {}).items():
        if scored_only and not entry["points"]:
            continue
        label = SIGNAL_LABELS.get(name, name)
        parts.append(f"{label} {entry['points']:+d}")
    head = f"signals {result['bonus']:+d}" + (" (capped)" if result.get("capped") else "")
    if not parts:
        return f"{head}: no signals scored"
    return f"{head}: " + ", ".join(parts)


def telegram_signal_line(result: dict[str, Any], *, limit: int = 4) -> str:
    """The key signals, strongest first, for the push message."""
    if not result.get("enabled"):
        return ""
    scored = [(name, entry) for name, entry in result.get("signals", {}).items() if entry["points"]]
    scored.sort(key=lambda item: abs(item[1]["points"]), reverse=True)
    shown = [
        f"{SIGNAL_LABELS.get(name, name)} {entry['points']:+d}" for name, entry in scored[:limit]
    ]
    if not shown:
        return f"signals {result['bonus']:+d}"
    extra = len(scored) - len(shown)
    return (
        f"signals {result['bonus']:+d}"
        + (" (capped)" if result.get("capped") else "")
        + " · "
        + ", ".join(shown)
        + (f" +{extra} more" if extra > 0 else "")
    )
