#!/usr/bin/env python3
"""Adapters that feed the role review from sibling skills instead of re-deriving.

| Role         | Reused skill                        | What it contributes              |
|--------------|-------------------------------------|----------------------------------|
| RESEARCHER   | stockbee-episodic-pivot-analyzer     | catalyst classification + EP score |
| TECHNICIAN   | technical-analyst (weekly_price_action) | weekly verdict + swing levels |
| RISK MANAGER | position-sizer                       | share count, risk $, constraints |

Every adapter is best-effort: on any failure it returns ``None`` (with the reason
in ``last_error``) and the role falls back to screener-field reasoning. Nothing
here is allowed to abort a run.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 — fixed, repo-local script paths only
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from config import repo_root

try:
    import yfinance

    HAS_YFINANCE = True
except ImportError:  # pragma: no cover - price enrichment is optional
    HAS_YFINANCE = False

EP_SCRIPT = "skills/stockbee-episodic-pivot-analyzer/scripts/analyze_ep.py"
SIZER_SCRIPT = "skills/position-sizer/scripts/position_sizer.py"
TECHNICAL_SCRIPTS = "skills/technical-analyst/scripts"


class AdapterResult(dict):
    """Dict subclass carrying an ``error`` key when the adapter degraded."""


def _script(relative: str) -> Path | None:
    path = repo_root() / relative
    return path if path.is_file() else None


def _run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 — argv list, no shell, repo-local script
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _newest_json(directory: Path, prefix: str) -> Path | None:
    matches = sorted(directory.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime)
    return matches[-1] if matches else None


# --------------------------------------------------------------------- prices


def fetch_daily_bars(ticker: str, lookback_days: int = 400) -> list[dict[str, Any]]:
    """Return daily OHLCV dicts (oldest first) via yfinance, or [] on failure."""
    if not HAS_YFINANCE:
        return []
    start = (date.today() - timedelta(days=lookback_days)).isoformat()
    try:
        frame = yfinance.Ticker(ticker).history(start=start, interval="1d", auto_adjust=False)
    except Exception:  # pragma: no cover - network/provider failure
        return []
    if frame is None or getattr(frame, "empty", True):
        return []
    bars: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        try:
            bars.append(
                {
                    "date": index.date().isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return bars


def latest_price(ticker: str) -> float | None:
    """Last available close for *ticker*, or None when unavailable."""
    bars = fetch_daily_bars(ticker, lookback_days=10)
    return bars[-1]["close"] if bars else None


# ------------------------------------------------- RESEARCHER: episodic pivot


def run_episodic_pivot(
    hit: dict[str, Any],
    *,
    headline: str | None = None,
    as_of: str | None = None,
    bars: list[dict[str, Any]] | None = None,
) -> AdapterResult | None:
    """Score the hit's catalyst with stockbee-episodic-pivot-analyzer."""
    script = _script(EP_SCRIPT)
    if script is None:
        return None
    as_of = as_of or date.today().isoformat()
    event = {
        "symbol": hit["ticker"],
        "event_date": as_of,
        "headline": headline or hit.get("catalyst_headline") or "",
        "summary": hit.get("company") or "",
        "gap_pct": hit.get("gap_pct"),
        "day_gain_pct": hit.get("change_pct"),
        "close": hit.get("price"),
        "volume": hit.get("volume"),
        "avg_volume_50": hit.get("avg_volume"),
    }
    with tempfile.TemporaryDirectory(prefix="lowcap-ep-") as tmp:
        tmp_path = Path(tmp)
        events_file = tmp_path / "events.json"
        events_file.write_text(json.dumps({"as_of": as_of, "events": [event]}), encoding="utf-8")
        cmd = [sys.executable, str(script), "--events-json", str(events_file)]
        if bars:
            prices_file = tmp_path / "prices.json"
            prices_file.write_text(json.dumps({hit["ticker"]: bars}), encoding="utf-8")
            cmd += ["--prices-json", str(prices_file)]
        cmd += ["--output-dir", str(tmp_path)]
        try:
            completed = _run(cmd)
        except subprocess.TimeoutExpired:
            return AdapterResult(error="episodic-pivot analyzer timed out")
        if completed.returncode != 0:
            return AdapterResult(error=f"episodic-pivot analyzer failed: {completed.stderr[-200:]}")
        report = _newest_json(tmp_path, "stockbee_episodic_pivot_")
        if report is None:
            return AdapterResult(error="episodic-pivot analyzer produced no JSON report")
        data = json.loads(report.read_text(encoding="utf-8"))

    for row in data.get("results") or []:
        if str(row.get("symbol", "")).upper() == hit["ticker"]:
            return AdapterResult(
                {
                    "catalyst_type": row.get("catalyst_type"),
                    "ep_type": row.get("ep_type"),
                    "state": row.get("state"),
                    "rating": row.get("rating"),
                    "composite_score": row.get("composite_score"),
                    "component_scores": row.get("component_scores"),
                    "catalyst_reasons": row.get("catalyst_reasons"),
                }
            )
    return AdapterResult(error="episodic-pivot analyzer returned no row for this symbol")


# ------------------------------------------- TECHNICIAN: weekly price action


def run_weekly_price_action(
    hit: dict[str, Any],
    bars: list[dict[str, Any]],
    *,
    direction: str = "long",
    as_of: str | None = None,
) -> AdapterResult | None:
    """Run technical-analyst's weekly price-action checks on *bars*."""
    scripts_dir = repo_root() / TECHNICAL_SCRIPTS
    module_path = scripts_dir / "weekly_price_action.py"
    if not module_path.is_file() or not bars:
        return None
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from weekly_price_action import run_weekly_price_action as _weekly
    except ImportError as exc:  # pragma: no cover - defensive
        return AdapterResult(error=f"weekly_price_action import failed: {exc}")

    try:
        result = _weekly(bars, direction, as_of or date.today().isoformat())
    except Exception as exc:  # pragma: no cover - upstream guard
        return AdapterResult(error=f"weekly_price_action failed: {type(exc).__name__}: {exc}")
    return AdapterResult(result)


# ------------------------------------------------- RISK MANAGER: sizing


def run_position_sizer(
    *,
    entry: float,
    stop: float,
    config: dict[str, Any],
    sector: str | None = None,
) -> AdapterResult | None:
    """Size the position with the position-sizer skill."""
    script = _script(SIZER_SCRIPT)
    if script is None or not entry or not stop or entry <= 0:
        return None
    tracker = config["tracker"]
    with tempfile.TemporaryDirectory(prefix="lowcap-size-") as tmp:
        cmd = [
            sys.executable,
            str(script),
            "--account-size",
            str(tracker["account_size"]),
            "--entry",
            f"{entry:.4f}",
            "--stop",
            f"{stop:.4f}",
            "--risk-pct",
            str(tracker["risk_pct"]),
            "--max-position-pct",
            str(tracker.get("max_position_pct", 10.0)),
            "--output-dir",
            tmp,
        ]
        if sector:
            cmd += ["--sector", sector]
        try:
            completed = _run(cmd, timeout=60)
        except subprocess.TimeoutExpired:
            return AdapterResult(error="position-sizer timed out")
        if completed.returncode != 0:
            return AdapterResult(error=f"position-sizer failed: {completed.stderr[-200:]}")
        report = _newest_json(Path(tmp), "position_sizer_")
        if report is None:
            return AdapterResult(error="position-sizer produced no JSON report")
        data = json.loads(report.read_text(encoding="utf-8"))

    shares = data.get("final_recommended_shares")
    return AdapterResult(
        {
            "shares": shares,
            "position_usd": data.get("final_position_value"),
            "risk_usd": data.get("final_risk_dollars"),
            "risk_pct": data.get("final_risk_pct"),
            "binding_constraint": data.get("binding_constraint"),
            "constraints_applied": data.get("constraints_applied"),
        }
    )


def utc_stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
