#!/usr/bin/env python3
"""Post-screen guards and run gates for one screener version.

A FinViz filter can only ever *narrow* a screen, and v2 was widened on purpose:

* ``sh_short_o15`` is gone. FinViz refreshes short interest twice a month, so a
  hard floor on a stale number excluded live squeezes while admitting names
  whose shorts had already covered. Short float is now read from the ownership
  view and *weighed* — a bonus on the Judge's confidence, never a veto.
* the float cap moved from 20M to 50M shares, and the relative-volume floor
  from 3x to 2x, which lets in names that have already run. The change cap
  refuses those: a stock up more than +25% on the day is not an entry, it is a
  chase.

v1 carries neither guard, and every hit records the version that produced it,
so a v1 call reviewed during a v2 run is still judged by v1's rules.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

try:  # pragma: no cover - stdlib on 3.9+, absent only on a stripped build
    from zoneinfo import ZoneInfo

    HAS_ZONEINFO = True
except ImportError:  # pragma: no cover
    HAS_ZONEINFO = False

from screener_variants import screener_version, version_guards

DEFAULT_TIMEZONE = "Europe/Zurich"


def hit_version(hit: dict[str, Any], config: dict[str, Any]) -> str:
    """The screener generation a hit belongs to.

    Tagged at screen time, so a stored call stays explainable after the active
    version moves on. Falls back to the active version for a fresh hit.
    """
    return str(hit.get("screener_version") or screener_version(config)).strip().lower()


def _number(value: Any) -> float | None:
    """Parse a FinViz cell into a float, or None. Never raises.

    The export writes percentages as ``22.40%`` and gaps as ``-``, and a
    guard that crashes on a dash would take the whole run down with it.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("%", "").replace(",", "").replace("+", "")
        if not text or text in {"-", "--", "n/a", "N/A"}:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    return number if number == number and abs(number) != float("inf") else None


# --- the change cap -------------------------------------------------------


def change_cap(config: dict[str, Any], version: str | None = None) -> float | None:
    """The day's-move ceiling for this version, or None to allow any move."""
    cap = _number(version_guards(config, version).get("max_change_pct"))
    return cap if cap and cap > 0 else None


def over_change_cap(hit: dict[str, Any], config: dict[str, Any]) -> bool:
    """True when *hit* has already run further today than its version allows.

    Reads one side only: the cap refuses chasing a vertical move, so a name
    down 40% is not capped. A missing or unparsable change column keeps the
    name — a data gap is not evidence, and the five roles still get to look.
    """
    cap = change_cap(config, hit_version(hit, config))
    if cap is None:
        return False
    change = _number(hit.get("change_pct"))
    return change is not None and change > cap


def apply_change_cap(
    hits: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split *hits* into (kept, skipped); skipped rows carry a reason."""
    kept: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for hit in hits:
        if not over_change_cap(hit, config):
            kept.append(hit)
            continue
        cap = change_cap(config, hit_version(hit, config))
        change = _number(hit.get("change_pct"))
        skipped.append(
            {
                "ticker": hit.get("ticker"),
                "variant": hit.get("variant"),
                "change_pct": change,
                "reason": f"already up {change:+.1f}% today (cap +{cap:.0f}%)",
            }
        )
    return kept, skipped


# --- the short-float bonus ------------------------------------------------


def short_float_points(hit: dict[str, Any], config: dict[str, Any]) -> int:
    """Confidence points earned by *hit*'s short float under its version.

    Rungs are read highest-first and only the top matching rung pays, so a 25%
    short float earns 10 points rather than 10 plus 5.
    """
    rungs = version_guards(config, hit_version(hit, config)).get("short_float_bonus") or []
    short_float = _number(hit.get("short_float_pct"))
    if short_float is None:
        return 0
    ladder = sorted(
        ((_number(rung.get("min_pct")), rung.get("bonus")) for rung in rungs),
        key=lambda pair: pair[0] if pair[0] is not None else -1.0,
        reverse=True,
    )
    for min_pct, bonus in ladder:
        if min_pct is not None and short_float >= min_pct:
            return int(_number(bonus) or 0)
    return 0


def apply_short_float_bonus(
    judge_verdict: dict[str, Any], hit: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Credit a crowded short back to the Judge's confidence.

    Applied before the Judge's gate, so a bonus can carry a name over the
    threshold — that is the point of replacing a hard filter with a score. It
    moves the number and records why; the gate alone decides TAKE vs SKIP.
    """
    points = short_float_points(hit, config)
    if points <= 0:
        return judge_verdict
    before = int(_number(judge_verdict.get("confidence")) or 0)
    judge_verdict["confidence"] = min(100, before + points)
    judge_verdict["short_float_bonus"] = {
        "short_float_pct": _number(hit.get("short_float_pct")),
        "points": points,
        "confidence_before": before,
        "confidence_after": judge_verdict["confidence"],
    }
    return judge_verdict


# --- the run gate ---------------------------------------------------------


def earliest_run(config: dict[str, Any], version: str | None = None) -> tuple[str, str] | None:
    """The (timezone, HH:MM) before which this version must not screen."""
    from screener_variants import version_block

    block = version_block(config, version).get("earliest_run") or {}
    time_text = str(block.get("time") or "").strip()
    if not time_text:
        return None
    return str(block.get("timezone") or DEFAULT_TIMEZONE), time_text


def earliest_run_block(
    config: dict[str, Any], *, now: datetime | None = None, version: str | None = None
) -> str | None:
    """Why this version must not screen yet, or None when it may.

    v2 orders by relative volume, and relative volume in the first hour after
    the US open is a ratio of a partial session against a full one — it ranks
    whatever opened first, not whatever is unusual. The gate waits for the
    number to mean something.
    """
    gate = earliest_run(config, version)
    if gate is None:
        return None
    zone_name, time_text = gate
    try:
        hour_text, _, minute_text = time_text.partition(":")
        hour, minute = int(hour_text), int(minute_text or 0)
    except ValueError:
        return None

    moment = now or datetime.now()
    zone = ZoneInfo(zone_name) if HAS_ZONEINFO else None
    if zone is not None:
        # A naive timestamp is read as local to the gate's own zone; an aware
        # one is converted, so a VPS running in UTC gates on Zurich time.
        moment = moment.replace(tzinfo=zone) if moment.tzinfo is None else moment.astimezone(zone)
    if (moment.hour, moment.minute) >= (hour, minute):
        return None
    return (
        f"{(version or screener_version(config))} does not screen before "
        f"{time_text} {zone_name} (now {moment.strftime('%H:%M')}): relative "
        "volume is too noisy in the first hour after the US open"
    )
