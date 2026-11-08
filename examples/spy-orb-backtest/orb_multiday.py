#!/usr/bin/env python3
"""Multi-day ORB engine: same opening-range-breakout entry, exits that can run overnight.

Entry (unchanged from orb_backtest.py): first 5-min close outside the 30-minute
opening range, at most one new entry per day, with the same FOMC / range-width
filters. Only one position is open at a time; signals while in a trade are ignored
unless the exit rule uses them (opposite breakout).

Exit rules (ExitRule.kind presets, all fields can be combined):
  eod        close at the end of the entry day (reproduces orb_backtest.py)
  trail      keep the trailing stop running across days (5-min ATR, or daily ATR)
  r_target   fixed target at r_multiple x the initial risk; stop stays put
  opposite   exit when a later day breaks out of its range the other way
  reverse    like opposite, but flip into the new direction (stop-and-reverse)
  ma         exit when the daily close crosses the ma_days daily moving average
Every rule keeps the initial stop (capped at stop_pct) and can add max_days.
Overnight gaps through a stop or target fill at the next open.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from orb_backtest import ORBConfig, _fill, add_atr, opening_range, prior_avg_daily_range


@dataclass
class ExitRule:
    kind: str = "trail"
    trail: str = "auto"  # "auto" (ATR trail if cfg.stop_mode == "atr"), "atr5", "daily_atr", "none"
    daily_atr_mult: float = 2.0
    daily_atr_period: int = 14
    r_multiple: float | None = None
    max_days: int | None = None  # 0 = same day; N = exit at the close N sessions after entry
    on_opposite: str | None = None  # None, "exit", "reverse"
    ma_days: int | None = None
    breakeven_r: float | None = None  # move stop to entry once the trade is +X R

    def resolved(self, cfg: ORBConfig) -> ExitRule:
        r = ExitRule(**self.__dict__)
        if r.trail == "auto":
            r.trail = "atr5" if cfg.stop_mode == "atr" else "none"
        if r.kind == "eod":
            r.max_days = 0
        elif r.kind == "r_target":
            r.r_multiple = r.r_multiple or 2.0
            r.trail = "none" if self.trail == "auto" else r.trail
        elif r.kind in ("opposite", "reverse"):
            r.on_opposite = "exit" if r.kind == "opposite" else "reverse"
            r.trail = "none" if self.trail == "auto" else r.trail
        elif r.kind == "ma":
            r.ma_days = r.ma_days or 10
            r.trail = "none" if self.trail == "auto" else r.trail
        return r


def _daily_atr(df: pd.DataFrame, period: int) -> dict:
    g = df.groupby(df.index.date)
    d = pd.DataFrame({"h": g["high"].max(), "l": g["low"].min(), "c": g["close"].last()})
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(
        axis=1
    )
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean().shift(1).to_dict()


class _Pos:
    def __init__(self, direction, entry, stop, day_idx, entry_ts, hi, lo):
        self.dir, self.entry, self.stop, self.initial_stop = direction, entry, stop, stop
        self.extreme, self.day_idx, self.entry_ts = entry, day_idx, entry_ts
        self.risk = abs(entry - stop)
        self.or_hi, self.or_lo = hi, lo


def backtest_multiday(df: pd.DataFrame, cfg: ORBConfig, rule: ExitRule) -> pd.DataFrame:
    rule = rule.resolved(cfg)
    if "atr" not in df.columns:
        df = add_atr(df, cfg.atr_period)
    adr = prior_avg_daily_range(df, cfg.adr_days) if cfg.max_or_width_rel is not None else {}
    datr = _daily_atr(df, rule.daily_atr_period) if rule.trail == "daily_atr" else {}
    closes = df.groupby(df.index.date)["close"].last()
    dma = closes.rolling(rule.ma_days).mean().to_dict() if rule.ma_days else {}
    cutoff = pd.Timestamp(cfg.last_entry_time).time()

    trades, pos = [], None
    days = list(df.groupby(df.index.date))

    def close_pos(price, ts, reason, di):
        nonlocal pos
        exit_px = _fill(float(price), -pos.dir, cfg)
        shares = cfg.position_size / pos.entry
        pnl = shares * (exit_px - pos.entry) * pos.dir - 2 * cfg.commission
        if reason == "stop" and (pos.stop - pos.initial_stop) * pos.dir > 1e-12:
            reason = "trail_stop" if pos.stop != pos.entry else "breakeven_stop"
        trades.append(
            {
                "date": pos.entry_ts.date().isoformat(),
                "entry_date": pos.entry_ts.date().isoformat(),
                "exit_date": ts.date().isoformat(),
                "direction": "long" if pos.dir == 1 else "short",
                "entry_time": pos.entry_ts.strftime("%H:%M"),
                "exit_time": ts.strftime("%H:%M"),
                "entry_price": pos.entry,
                "initial_stop": pos.initial_stop,
                "exit_price": exit_px,
                "exit_reason": reason,
                "days_held": di - pos.day_idx,
                "pnl": pnl,
                "return_pct": pnl / cfg.position_size * 100,
            }
        )
        pos = None

    def open_pos(direction, raw_price, bar, ts, di, hi, lo):
        nonlocal pos
        entry = _fill(float(raw_price), direction, cfg)
        pct_stop = entry * (1 - direction * cfg.stop_pct / 100)
        if cfg.stop_mode == "range":
            stop = lo if direction == 1 else hi
        elif cfg.stop_mode == "atr" and not pd.isna(bar["atr"]):
            atr_stop = entry - direction * cfg.atr_mult * float(bar["atr"])
            stop = max(atr_stop, pct_stop) if direction == 1 else min(atr_stop, pct_stop)
        else:
            stop = pct_stop
        if cfg.stop_mode == "range":  # still never risk more than stop_pct
            stop = max(stop, pct_stop) if direction == 1 else min(stop, pct_stop)
        pos = _Pos(direction, entry, stop, di, ts, hi, lo)

    for di, (d, day) in enumerate(days):
        hi, lo, after = opening_range(day, cfg.range_minutes)
        can_enter = d.isoformat() not in cfg.skip_dates and hi is not None
        if can_enter and cfg.max_or_width_rel is not None:
            a = adr.get(d)
            width = (hi - lo) / float(day["open"].iloc[0]) * 100
            can_enter = (
                a is not None and not pd.isna(a) and a > 0 and width / a <= cfg.max_or_width_rel
            )
        entered_today = False
        or_end = day.index[0].normalize() + pd.Timedelta(hours=9, minutes=30 + cfg.range_minutes)
        bars = list(day.iterrows())
        for bi, (ts, b) in enumerate(bars):
            is_last = bi == len(bars) - 1
            just_entered = False
            # ---- manage an open position (not on its own entry bar)
            if pos is not None and ts != pos.entry_ts:
                o, h, low, c = (
                    float(b["open"]),
                    float(b["high"]),
                    float(b["low"]),
                    float(b["close"]),
                )
                target = (
                    pos.entry + pos.dir * rule.r_multiple * pos.risk if rule.r_multiple else None
                )
                if pos.dir == 1 and low <= pos.stop:
                    close_pos(min(pos.stop, o), ts, "stop", di)
                elif pos.dir == -1 and h >= pos.stop:
                    close_pos(max(pos.stop, o), ts, "stop", di)
                elif target is not None and pos.dir == 1 and h >= target:
                    close_pos(max(target, o), ts, "target", di)
                elif target is not None and pos.dir == -1 and low <= target:
                    close_pos(min(target, o), ts, "target", di)
                elif (
                    rule.on_opposite
                    and hi is not None
                    and ts >= or_end
                    and ((pos.dir == 1 and c < lo) or (pos.dir == -1 and c > hi))
                ):
                    old_dir = pos.dir
                    close_pos(c, ts, "opposite_breakout", di)
                    if (
                        rule.on_opposite == "reverse"
                        and can_enter
                        and not entered_today
                        and ts.time() <= cutoff
                    ):
                        open_pos(-old_dir, c, b, ts, di, hi, lo)
                        entered_today = just_entered = True
                else:
                    # ratchet after the bar
                    if rule.trail == "atr5" and not pd.isna(b["atr"]):
                        dist = cfg.atr_mult * float(b["atr"])
                    elif rule.trail == "daily_atr" and not pd.isna(datr.get(d, float("nan"))):
                        dist = rule.daily_atr_mult * float(datr[d])
                    else:
                        dist = None
                    if pos.dir == 1:
                        pos.extreme = max(pos.extreme, h)
                    else:
                        pos.extreme = min(pos.extreme, low)
                    if dist is not None:
                        new = pos.extreme - pos.dir * dist
                        pos.stop = max(pos.stop, new) if pos.dir == 1 else min(pos.stop, new)
                    if (
                        rule.breakeven_r
                        and (pos.extreme - pos.entry) * pos.dir >= rule.breakeven_r * pos.risk
                    ):
                        pos.stop = (
                            max(pos.stop, pos.entry) if pos.dir == 1 else min(pos.stop, pos.entry)
                        )
            # ---- end-of-day checks for an open position
            if pos is not None and is_last and not just_entered:
                held = di - pos.day_idx
                if rule.max_days is not None and held >= rule.max_days:
                    close_pos(float(b["close"]), ts, "eod" if rule.max_days == 0 else "time", di)
                elif rule.ma_days and d in dma and not pd.isna(dma[d]):
                    c = float(b["close"])
                    if (pos.dir == 1 and c < dma[d]) or (pos.dir == -1 and c > dma[d]):
                        close_pos(c, ts, "ma_cross", di)
            elif pos is not None and is_last and just_entered and rule.max_days == 0:
                close_pos(float(b["close"]), ts, "eod", di)
            # ---- new entry
            if (
                pos is None
                and can_enter
                and not entered_today
                and ts >= or_end
                and ts.time() <= cutoff
            ):
                c = float(b["close"])
                if c > hi or (c < lo and cfg.allow_short):
                    open_pos(1 if c > hi else -1, c, b, ts, di, hi, lo)
                    entered_today = True
                    if is_last and rule.max_days == 0:
                        close_pos(c, ts, "eod", di)
            # the backtester stops looking for entries once past the cutoff
            if pos is None and ts.time() > cutoff:
                can_enter = False
    if pos is not None:
        ts, b = days[-1][1].index[-1], days[-1][1].iloc[-1]
        close_pos(float(b["close"]), ts, "end_of_data", len(days) - 1)
    return pd.DataFrame(trades)
