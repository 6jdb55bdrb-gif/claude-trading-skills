"""ICT Silver Bullet strategy engine (deterministic, bar-based, no look-ahead).

The Silver Bullet is a time-boxed intraday setup traded inside three one-hour
New York windows (03:00-04:00, 10:00-11:00, 14:00-15:00 America/New_York):

1. Mark liquidity formed *before* the window (the high/low of a pre-window
   reference range).
2. Inside the window, wait for price to run one side of that liquidity
   (the "sweep").
3. Require displacement back the other way that leaves a Fair Value Gap
   (FVG) and, optionally, a market-structure shift (MSS) through the swing
   that preceded the sweep.
4. Enter on the retrace into the FVG (limit order at the FVG edge or its
   consequent encroachment / midpoint) -- the fill must happen inside the
   window.
5. Stop beyond the sweep extreme (plus an ATR buffer); target the opposing
   pre-window liquidity, or a fixed R multiple.

Simulation conventions (chosen to be conservative):

* Bar timestamps are bar OPEN times. A bar belongs to the window if its open
  is in ``[window_start, window_end)``.
* Every input used to define a setup is known at the close of the FVG's third
  candle; the earliest possible fill is the following bar.
* If a bar's range touches both stop and target, the stop is assumed first.
* On the fill bar only the stop is evaluated (the intrabar order of fill vs.
  target is unknown, so a same-bar win is never credited).
* Limit fills are always at the limit price (no price improvement on gaps).
* After the fill bar, a gap through the stop exits at the bar open (worse
  than the stop).
* A pending limit order is cancelled if price reaches the target before the
  entry fills (the move left without us) or the window closes.
* Positions still open at the flat deadline are closed at the last bar's
  close before that deadline.
* Costs are charged per side in basis points of price and expressed in R.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import time, timedelta

import numpy as np
import pandas as pd

NY_TZ = "America/New_York"

DEFAULT_WINDOWS: dict[str, tuple[time, time]] = {
    "london": (time(3, 0), time(4, 0)),
    "am": (time(10, 0), time(11, 0)),
    "pm": (time(14, 0), time(15, 0)),
}


@dataclass
class SilverBulletParams:
    """Tunable rules. Defaults are the 'canonical' robust configuration."""

    windows: tuple[str, ...] = ("london", "am", "pm")
    ref_lookback_minutes: int = 120  # pre-window liquidity reference range
    sweep_lead_minutes: int = 30  # sweep may start this long before the window
    require_sweep: bool = True
    require_mss: bool = True
    mss_lookback_bars: int = 5  # swing that must be broken after the sweep
    atr_period: int = 14
    min_fvg_atr: float = 0.10  # FVG height >= this * ATR
    displacement_atr: float = 0.50  # displacement candle body >= this * ATR
    entry_mode: str = "edge"  # "edge" (proximal FVG edge) or "ce" (midpoint)
    stop_buffer_atr: float = 0.10
    max_risk_atr: float = 4.0  # skip setups whose stop is absurdly wide
    target_mode: str = "liquidity"  # "liquidity" (opposing ref level) or "rr"
    min_rr: float = 1.5  # liquidity target must offer at least this R
    rr_target: float = 2.0  # used when target_mode == "rr"
    flat_minutes_after_window: int = 60
    cost_bps: float = 1.0  # per side, in basis points of price
    max_cost_r: float = 0.10  # skip setups whose round-trip cost exceeds this R
    bias_filter: str = "none"  # "none" or "sma" (trade with the daily trend)
    bias_sma_days: int = 20
    include_weekends: bool = False

    def validate(self) -> None:
        unknown = set(self.windows) - set(DEFAULT_WINDOWS)
        if unknown:
            raise ValueError(f"unknown window(s): {sorted(unknown)}")
        if self.entry_mode not in ("edge", "ce"):
            raise ValueError("entry_mode must be 'edge' or 'ce'")
        if self.target_mode not in ("liquidity", "rr"):
            raise ValueError("target_mode must be 'liquidity' or 'rr'")
        if self.bias_filter not in ("none", "sma"):
            raise ValueError("bias_filter must be 'none' or 'sma'")
        if self.sweep_lead_minutes < 0 or self.sweep_lead_minutes >= self.ref_lookback_minutes:
            raise ValueError("sweep_lead_minutes must be in [0, ref_lookback_minutes)")
        if self.ref_lookback_minutes <= 0 or self.atr_period <= 0:
            raise ValueError("lookback and ATR period must be positive")
        if self.min_rr <= 0 or self.rr_target <= 0:
            raise ValueError("R multiples must be positive")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trade:
    date: str
    window: str
    direction: str  # "long" | "short"
    setup_time: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    target: float
    exit: float
    exit_reason: str  # "target" | "stop" | "time"
    risk: float
    r_gross: float
    r_net: float
    fvg_size_atr: float
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Data preparation
# --------------------------------------------------------------------------- #


def prepare_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise an OHLC frame: lower-case columns, tz-aware NY index, sorted."""
    if df.empty:
        raise ValueError("price frame is empty")
    out = df.rename(columns=str.lower).copy()
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"missing OHLC columns: {sorted(missing)}")
    if not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError("index must be a DatetimeIndex")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    out.index = out.index.tz_convert(NY_TZ)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out.dropna(subset=["open", "high", "low", "close"])
    return out[["open", "high", "low", "close"]].astype(float)


def wilder_atr(df: pd.DataFrame, period: int) -> np.ndarray:
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    prev_close = np.concatenate(([close[0]], close[:-1]))
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr = pd.Series(tr).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return atr.values


def resample_bars(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample OHLC bars (index = bar open) to a coarser timeframe."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    out = df.resample(rule, label="left", closed="left").agg(agg)
    return out.dropna()


# --------------------------------------------------------------------------- #
# Setup detection + simulation
# --------------------------------------------------------------------------- #


def _cost_r(entry: float, exit_px: float, risk: float, cost_bps: float) -> float:
    return (entry + exit_px) * cost_bps / 1e4 / risk


def _simulate_window(
    ts: pd.DatetimeIndex,
    o: np.ndarray,
    h: np.ndarray,
    lo: np.ndarray,
    c: np.ndarray,
    atr: np.ndarray,
    day: pd.Timestamp,
    wname: str,
    p: SilverBulletParams,
    bias: int = 0,
) -> tuple[Trade | None, dict]:
    """Scan one window on one day. Returns (trade or None, diagnostics)."""
    diag = {"date": str(day.date()), "window": wname, "status": "no_data"}
    start_t, end_t = DEFAULT_WINDOWS[wname]
    ws = day.replace(hour=start_t.hour, minute=start_t.minute)
    we = day.replace(hour=end_t.hour, minute=end_t.minute)
    flat = we + timedelta(minutes=p.flat_minutes_after_window)
    ref_start = ws - timedelta(minutes=p.ref_lookback_minutes)
    sweep_start = ws - timedelta(minutes=p.sweep_lead_minutes)

    r0, s0, r1 = ts.searchsorted(ref_start), ts.searchsorted(sweep_start), ts.searchsorted(ws)
    w1 = ts.searchsorted(we)
    f1 = ts.searchsorted(flat)
    if s0 - r0 < 3 or w1 - r1 < 3:
        return None, diag
    # liquidity pools: formed before the sweep zone; they can be run from
    # sweep_start onwards (e.g. the 09:30 open running pre-market highs/lows)
    ref_high = float(h[r0:s0].max())
    ref_low = float(lo[r0:s0].min())
    diag.update(status="no_setup", ref_high=ref_high, ref_low=ref_low)

    bull_swept = bear_swept = False
    sweep_low = np.inf
    sweep_high = -np.inf
    sweep_low_i = sweep_high_i = -1
    setups_seen = 0

    i = s0
    while i < w1:
        # update sweep state using bar i
        if lo[i] < ref_low:
            bull_swept = True
            if lo[i] < sweep_low:
                sweep_low, sweep_low_i = float(lo[i]), i
        if h[i] > ref_high:
            bear_swept = True
            if h[i] > sweep_high:
                sweep_high, sweep_high_i = float(h[i]), i

        if i < r1 + 1 or not np.isfinite(atr[i]) or atr[i] <= 0:
            i += 1
            continue

        setup = None
        a = float(atr[i])
        # ---- bullish FVG: low[i] > high[i-2], displacement up on i-1
        gap = lo[i] - h[i - 2]
        body = c[i - 1] - o[i - 1]
        if bias >= 0 and gap >= p.min_fvg_atr * a and body >= p.displacement_atr * a:
            ok = True
            stop_anchor = min(lo[i - 2], lo[i - 1])
            if p.require_sweep:
                ok = bull_swept and sweep_low_i <= i - 1
                stop_anchor = min(stop_anchor, sweep_low)
            if ok and p.require_mss:
                ok = _mss_ok(h, c, i, sweep_low_i if p.require_sweep else i - 2, p, r0, long=True)
            if ok:
                setup = _build_setup("long", i, lo, h, a, stop_anchor, ref_high, p)
        # ---- bearish FVG: high[i] < low[i-2], displacement down on i-1
        if setup is None:
            gap = lo[i - 2] - h[i]
            body = o[i - 1] - c[i - 1]
            if bias <= 0 and gap >= p.min_fvg_atr * a and body >= p.displacement_atr * a:
                ok = True
                stop_anchor = max(h[i - 2], h[i - 1])
                if p.require_sweep:
                    ok = bear_swept and sweep_high_i <= i - 1
                    stop_anchor = max(stop_anchor, sweep_high)
                if ok and p.require_mss:
                    ok = _mss_ok(
                        lo, c, i, sweep_high_i if p.require_sweep else i - 2, p, r0, long=False
                    )
                if ok:
                    setup = _build_setup("short", i, lo, h, a, stop_anchor, ref_low, p)

        if setup is None:
            i += 1
            continue
        setups_seen += 1
        trade, next_i = _run_order(setup, i, ts, o, h, lo, c, w1, f1, day, wname, p)
        if trade is not None:
            diag.update(status="traded", setups_seen=setups_seen)
            return trade, diag
        i = max(next_i, i + 1)

    if setups_seen:
        diag.update(status="setup_unfilled", setups_seen=setups_seen)
    return None, diag


def _mss_ok(level_arr, c, i, anchor_i, p, floor_i, long: bool) -> bool:
    """Market-structure shift: displacement closes through the swing that
    preceded the sweep (highest high / lowest low of ``mss_lookback_bars``
    bars before the sweep bar)."""
    lo_i = max(floor_i, anchor_i - p.mss_lookback_bars)
    if anchor_i <= lo_i:
        return False
    if long:
        swing = level_arr[lo_i:anchor_i].max()
        return max(c[i - 1], c[i]) > swing
    swing = level_arr[lo_i:anchor_i].min()
    return min(c[i - 1], c[i]) < swing


def _build_setup(direction, i, lo, h, a, stop_anchor, liq_target, p):
    if direction == "long":
        top, bottom = float(lo[i]), float(h[i - 2])
        entry = top if p.entry_mode == "edge" else (top + bottom) / 2
        stop = float(stop_anchor) - p.stop_buffer_atr * a
        risk = entry - stop
        if risk <= 0 or risk > p.max_risk_atr * a:
            return None
        if p.target_mode == "rr":
            target = entry + p.rr_target * risk
        else:
            target = liq_target
            if (target - entry) / risk < p.min_rr:
                return None
    else:
        top, bottom = float(lo[i - 2]), float(h[i])
        entry = bottom if p.entry_mode == "edge" else (top + bottom) / 2
        stop = float(stop_anchor) + p.stop_buffer_atr * a
        risk = stop - entry
        if risk <= 0 or risk > p.max_risk_atr * a:
            return None
        if p.target_mode == "rr":
            target = entry - p.rr_target * risk
        else:
            target = liq_target
            if (entry - target) / risk < p.min_rr:
                return None
    if 2 * entry * p.cost_bps / 1e4 > p.max_cost_r * risk:
        return None  # stop too tight for the instrument's costs
    return {
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "target": float(target),
        "risk": risk,
        "fvg_size_atr": (top - bottom) / a,
    }


def _run_order(s, i, ts, o, h, lo, c, w1, f1, day, wname, p):
    """Work the limit order from bar i+1; manage the position if filled.

    Returns (trade or None, index to resume scanning from)."""
    long = s["direction"] == "long"
    entry, stop, target = s["entry"], s["stop"], s["target"]
    j = i + 1
    fill_j = None
    fill_px = entry
    while j < w1:
        if long:
            if h[j] >= target and lo[j] > entry:
                return None, j  # ran to target without us -> cancel
            if lo[j] <= entry:
                fill_j = j
                break
        else:
            if lo[j] <= target and h[j] < entry:
                return None, j
            if h[j] >= entry:
                fill_j = j
                break
        j += 1
    if fill_j is None:
        return None, w1

    risk = s["risk"]
    exit_px = exit_reason = None
    exit_j = fill_j
    # fill bar: stop only (conservative)
    if (long and lo[fill_j] <= stop) or (not long and h[fill_j] >= stop):
        exit_px, exit_reason = stop, "stop"
    else:
        k = fill_j + 1
        last = fill_j
        while k < f1:
            last = k
            if long:
                if o[k] <= stop:
                    exit_px, exit_reason = o[k], "stop"
                elif lo[k] <= stop:
                    exit_px, exit_reason = stop, "stop"
                elif o[k] >= target:
                    exit_px, exit_reason = o[k], "target"
                elif h[k] >= target:
                    exit_px, exit_reason = target, "target"
            else:
                if o[k] >= stop:
                    exit_px, exit_reason = o[k], "stop"
                elif h[k] >= stop:
                    exit_px, exit_reason = stop, "stop"
                elif o[k] <= target:
                    exit_px, exit_reason = o[k], "target"
                elif lo[k] <= target:
                    exit_px, exit_reason = target, "target"
            if exit_reason:
                break
            k += 1
        exit_j = last
        if exit_reason is None:
            exit_px, exit_reason = c[last], "time"

    sign = 1.0 if long else -1.0
    r_gross = sign * (exit_px - fill_px) / risk
    r_net = r_gross - _cost_r(fill_px, exit_px, risk, p.cost_bps)
    trade = Trade(
        date=str(day.date()),
        window=wname,
        direction=s["direction"],
        setup_time=ts[i].isoformat(),
        entry_time=ts[fill_j].isoformat(),
        exit_time=ts[exit_j].isoformat(),
        entry=round(float(fill_px), 6),
        stop=round(float(stop), 6),
        target=round(float(target), 6),
        exit=round(float(exit_px), 6),
        exit_reason=exit_reason,
        risk=round(float(risk), 6),
        r_gross=round(float(r_gross), 4),
        r_net=round(float(r_net), 4),
        fvg_size_atr=round(float(s["fvg_size_atr"]), 3),
    )
    return trade, exit_j


def daily_bias(bars: pd.DataFrame, p: SilverBulletParams) -> dict:
    """+1 / -1 per NY day: previous completed day's close vs. its N-day SMA.

    Uses only days strictly before the trading day (no look-ahead)."""
    closes = bars["close"].groupby(bars.index.normalize()).last()
    sma = closes.rolling(p.bias_sma_days, min_periods=p.bias_sma_days).mean()
    sign = np.sign(closes - sma).shift(1)
    return {d: int(v) for d, v in sign.items() if np.isfinite(v) and v != 0}


def run_backtest(
    df: pd.DataFrame, params: SilverBulletParams | None = None
) -> tuple[list[Trade], list[dict]]:
    """Run the Silver Bullet over every NY calendar day in ``df``."""
    p = params or SilverBulletParams()
    p.validate()
    bars = prepare_bars(df)
    atr = wilder_atr(bars, p.atr_period)
    ts = bars.index
    o, h, lo, c = (bars[k].values for k in ("open", "high", "low", "close"))
    days = pd.DatetimeIndex(ts.normalize().unique())
    biases = daily_bias(bars, p) if p.bias_filter != "none" else {}
    trades: list[Trade] = []
    diags: list[dict] = []
    for day in days:
        if not p.include_weekends and day.weekday() >= 5:
            continue
        bias = biases.get(day, 0) if p.bias_filter != "none" else 0
        if p.bias_filter != "none" and bias == 0:
            continue  # not enough history for a bias -> stand aside
        for wname in p.windows:
            trade, diag = _simulate_window(ts, o, h, lo, c, atr, day, wname, p, bias)
            diags.append(diag)
            if trade is not None:
                trades.append(trade)
    return trades, diags


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def summarize(trades: list[Trade], seed: int = 7, n_boot: int = 2000) -> dict:
    """Per-trade R statistics with a bootstrap CI on expectancy."""
    r = np.array([t.r_net for t in trades], dtype=float)
    n = len(r)
    if n == 0:
        return {"trades": 0}
    wins, losses = r[r > 0], r[r <= 0]
    equity = np.cumsum(r)
    dd = equity - np.maximum.accumulate(np.concatenate(([0.0], equity)))[1:]
    gross_loss = -losses.sum()
    rng = np.random.default_rng(seed)
    boot = (
        rng.choice(r, size=(n_boot, n), replace=True).mean(axis=1)
        if n > 1
        else np.array([r.mean()])
    )
    std = r.std(ddof=1) if n > 1 else 0.0
    return {
        "trades": int(n),
        "win_rate": round(float(len(wins) / n), 4),
        "expectancy_r": round(float(r.mean()), 4),
        "median_r": round(float(np.median(r)), 4),
        "total_r": round(float(r.sum()), 2),
        "profit_factor": round(float(wins.sum() / gross_loss), 3) if gross_loss > 0 else None,
        "max_drawdown_r": round(float(dd.min()), 2),
        "t_stat": round(float(r.mean() / (std / np.sqrt(n))), 2) if std > 0 else None,
        "expectancy_ci95": [
            round(float(np.percentile(boot, 2.5)), 4),
            round(float(np.percentile(boot, 97.5)), 4),
        ],
        "exit_mix": {
            k: int(sum(1 for t in trades if t.exit_reason == k)) for k in ("target", "stop", "time")
        },
        "long_short": {
            "long": int(sum(1 for t in trades if t.direction == "long")),
            "short": int(sum(1 for t in trades if t.direction == "short")),
        },
    }
