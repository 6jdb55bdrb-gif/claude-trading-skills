#!/usr/bin/env python3
"""IVB (Initial-balance Volume Breakout) backtester.

Recreates the intraday "IVB" bias model Fabio Valentini describes in the
World Class Edge interview ("Inside the Mind of a World-Class Trader"):

  1. US index volume arrives at a predictable time -> the opening battle
     defines an Initial Balance (IB) high / low (passive liquidity walls).
  2. Once one side breaks, the day tends to continue in that direction.
  3. Fake breakouts are the main failure mode -> require a *strong*
     breakout bar (his "strong delta bar / aggressive big-trade
     participation"). Order-flow delta is not in OHLCV data, so it is
     proxied by relative volume + close location inside the bar.
  4. Stop goes just beyond the aggression (breakout) bar -> asymmetric R.
  5. Hold for the directional day (exit at the close).

Options walls, MBO big-trade prints and discretionary management from the
interview cannot be reproduced from OHLCV bars and are NOT modelled.

Data sources:
  --source yahoo   : yfinance 60m bars (~730 calendar days, free)
  --source alpaca  : Alpaca SIP 1Min/5Min bars (needs APCA keys; 2016+)
  --source csv     : any CSV with timestamp,open,high,low,close,volume (ET)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import time
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError:  # pragma: no cover
    print("pandas/numpy required: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

ET = "America/New_York"
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------
@dataclass
class Params:
    ib_minutes: int = 60  # initial-balance length
    rvol_min: float = 0.0  # breakout bar volume / avg same-time-of-day volume
    rvol_lookback: int = 20  # days for the time-of-day volume average
    clv_min: float = 0.0  # close location in bar (long: >= clv, short: <= 1-clv)
    stop_mode: str = "ib_opposite"  # ib_opposite | ib_mid | breakout_bar
    target_r: float = 0.0  # 0 = no target, hold to close
    last_entry: str = "15:00"  # no new entries at/after this bar start
    allow_short: bool = True
    cost_bps: float = 1.0  # one-way slippage+commission in bps of price
    risk_pct: float = 1.0  # % equity risked per trade
    max_leverage: float = 4.0
    garch_filter: str = "none"  # none | high | low (vs rolling median forecast)

    def label(self) -> str:
        parts = [f"IB{self.ib_minutes}", f"stop={self.stop_mode}"]
        if self.rvol_min:
            parts.append(f"rvol>={self.rvol_min:g}")
        if self.clv_min:
            parts.append(f"clv>={self.clv_min:g}")
        if self.target_r:
            parts.append(f"T={self.target_r:g}R")
        if not self.allow_short:
            parts.append("long-only")
        if self.garch_filter != "none":
            parts.append(f"garch={self.garch_filter}")
        return " ".join(parts)


@dataclass
class Trade:
    date: str
    side: int
    entry_time: str
    entry: float
    stop: float
    exit_time: str
    exit: float
    exit_reason: str
    r_multiple: float
    ret_pct: float  # equity return of this trade (sized)
    rvol: float
    clv: float
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].copy()
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize(ET) if idx.tz is None else idx.tz_convert(ET)
    df.index = idx
    df = df[~df.index.duplicated()].sort_index()
    t = df.index.time
    df = df[(t >= RTH_OPEN) & (t < RTH_CLOSE)]
    return df.dropna()


def load_yahoo(symbol: str, interval: str = "60m", period: str = "730d") -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(
        symbol, interval=interval, period=period, progress=False, auto_adjust=False, prepost=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return _normalize(df)


def load_yahoo_daily(symbol: str, start: str = "2015-01-01") -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(symbol, start=start, interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.DatetimeIndex(df.index).tz_localize(None)
    return df.rename(columns=str.lower)


def load_alpaca(
    symbol: str, start: str, end: str, timeframe: str = "1Min", cache_dir: Path | None = None
) -> pd.DataFrame:
    """Alpaca v2 bars. Keys from APCA_API_KEY_ID / APCA_API_SECRET_KEY."""
    import requests

    key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_SECRET_KEY")
    if not key:
        print("Missing APCA_API_KEY_ID / ALPACA_API_KEY", file=sys.stderr)
        sys.exit(1)
    headers = {"APCA-API-KEY-ID": key}
    if secret:
        headers["APCA-API-SECRET-KEY"] = secret
    cache = None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = cache_dir / f"alpaca_{symbol}_{timeframe}_{start}_{end}.parquet"
        if cache.exists():
            return pd.read_parquet(cache)
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    params = {
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "limit": 10000,
        "adjustment": "all",
        "feed": os.environ.get("ALPACA_FEED", "sip"),
    }
    rows, token = [], None
    while True:
        if token:
            params["page_token"] = token
        for attempt in range(5):
            r = requests.get(url, headers=headers, params=params, timeout=60)
            if r.status_code == 429:
                import time as _t

                _t.sleep(2**attempt)
                continue
            break
        if r.status_code != 200:
            print(f"Alpaca error {r.status_code}: {r.text[:300]}", file=sys.stderr)
            sys.exit(1)
        js = r.json()
        rows.extend(js.get("bars") or [])
        token = js.get("next_page_token")
        if not token:
            break
    df = pd.DataFrame(rows).rename(
        columns={"t": "ts", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
    )
    df.index = pd.to_datetime(df.pop("ts"), utc=True)
    df = _normalize(df)
    if cache:
        df.to_parquet(cache)
    return df


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=[0], index_col=0)
    return _normalize(df)


def resample(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df.groupby(df.index.date).apply(
        lambda g: g.resample(
            f"{minutes}min", origin=g.index[0].normalize() + pd.Timedelta(hours=9, minutes=30)
        ).agg(agg)
    )
    out.index = out.index.droplevel(0)
    return out.dropna()


# --------------------------------------------------------------------------
# GARCH(1,1) next-day volatility forecast (walk-forward, no lookahead)
# --------------------------------------------------------------------------
def garch_forecast(daily_close: pd.Series, refit_every: int = 21, min_obs: int = 500) -> pd.Series:
    """Return series indexed by date D = conditional vol forecast for day D using data < D."""
    from arch import arch_model

    ret = 100 * np.log(daily_close).diff().dropna()
    out = pd.Series(index=ret.index, dtype=float)
    res = None
    for i in range(min_obs, len(ret)):
        if res is None or (i - min_obs) % refit_every == 0:
            am = arch_model(ret.iloc[:i], vol="GARCH", p=1, q=1, dist="t", rescale=False)
            res = am.fit(disp="off")
            params = res.params
        # one-step recursion with fixed params using info up to i-1
        omega, alpha, beta = params["omega"], params["alpha[1]"], params["beta[1]"]
        if i == min_obs or (i - min_obs) % refit_every == 0:
            sig2 = res.conditional_volatility.iloc[-1] ** 2
            eps2 = (ret.iloc[i - 1] - params["mu"]) ** 2
        else:
            eps2 = (ret.iloc[i - 1] - params["mu"]) ** 2
        sig2 = omega + alpha * eps2 + beta * sig2
        out.iloc[i] = math.sqrt(sig2)
    out.index = pd.DatetimeIndex(out.index).date
    return out.dropna()


# --------------------------------------------------------------------------
# Core engine
# --------------------------------------------------------------------------
def _hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def add_rvol(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    df = df.copy()
    tod = df.index.strftime("%H:%M")
    df["tod"] = tod
    avg = df.groupby("tod")["volume"].transform(
        lambda s: s.shift(1).rolling(lookback, min_periods=max(5, lookback // 2)).mean()
    )
    df["rvol"] = df["volume"] / avg
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    df["clv"] = ((df["close"] - df["low"]) / rng).fillna(0.5)
    return df


def run_backtest(df: pd.DataFrame, p: Params, garch: pd.Series | None = None) -> list[Trade]:
    df = add_rvol(df, p.rvol_lookback)
    last_entry = _hhmm(p.last_entry)
    gmed = garch.rolling(60, min_periods=20).median().shift(1) if garch is not None else None
    trades: list[Trade] = []
    for d, day in df.groupby(df.index.date):
        if len(day) < 3:
            continue
        if p.garch_filter != "none" and garch is not None:
            if d not in garch.index or pd.isna(gmed.get(d)):
                continue
            hi_vol = garch[d] > gmed[d]
            if (p.garch_filter == "high") != hi_vol:
                continue
        start = day.index[0].normalize() + pd.Timedelta(hours=9, minutes=30)
        ib_end = start + pd.Timedelta(minutes=p.ib_minutes)
        if day.index[0] != start:
            continue  # partial / late-start session
        ib = day[day.index < ib_end]
        rest = day[day.index >= ib_end]
        if ib.empty or rest.empty:
            continue
        ib_hi, ib_lo = ib["high"].max(), ib["low"].min()
        ib_mid = (ib_hi + ib_lo) / 2
        trade = None
        for i, (ts, bar) in enumerate(rest.iterrows()):
            if ts.time() >= last_entry:
                break
            side = 0
            if bar["close"] > ib_hi:
                side = 1
            elif bar["close"] < ib_lo and p.allow_short:
                side = -1
            elif bar["close"] < ib_lo:
                break  # first break was down in long-only mode -> no trade
            if not side:
                continue
            # first close outside the IB decides the day: apply strength filter once
            rv = bar["rvol"] if not pd.isna(bar["rvol"]) else 0.0
            clv = bar["clv"] if side == 1 else 1 - bar["clv"]
            if rv < p.rvol_min or clv < p.clv_min:
                break
            entry = bar["close"]
            if p.stop_mode == "ib_opposite":
                stop = ib_lo if side == 1 else ib_hi
            elif p.stop_mode == "ib_mid":
                stop = ib_mid
            elif p.stop_mode == "breakout_bar":
                stop = bar["low"] if side == 1 else bar["high"]
            else:
                raise ValueError(p.stop_mode)
            risk = (entry - stop) * side
            if risk <= 0:
                break
            trade = (side, ts, entry, stop, risk, rv, clv, rest.iloc[i + 1 :])
            break
        if trade is None:
            continue
        side, ts, entry, stop, risk, rv, clv, after = trade
        target = entry + side * p.target_r * risk if p.target_r else None
        exit_px, exit_ts, reason = None, None, "close"
        for ts2, b in after.iterrows():
            hit_stop = (b["low"] <= stop) if side == 1 else (b["high"] >= stop)
            hit_tgt = target is not None and (
                (b["high"] >= target) if side == 1 else (b["low"] <= target)
            )
            if hit_stop:  # conservative: stop first when both inside one bar
                gap_through = (b["open"] < stop) if side == 1 else (b["open"] > stop)
                exit_px, exit_ts, reason = (b["open"] if gap_through else stop), ts2, "stop"
                break
            if hit_tgt:
                gap_through = (b["open"] > target) if side == 1 else (b["open"] < target)
                exit_px, exit_ts, reason = (b["open"] if gap_through else target), ts2, "target"
                break
        if exit_px is None:
            last = after.iloc[-1] if len(after) else rest.loc[ts]
            exit_px, exit_ts = last["close"], (after.index[-1] if len(after) else ts)
        cost = p.cost_bps / 1e4 * (entry + exit_px)
        pnl_ps = (exit_px - entry) * side - cost
        r_mult = pnl_ps / risk
        # position size: risk_pct of equity, capped by leverage
        frac_risk = p.risk_pct / 100.0
        notional_frac = min(frac_risk / (risk / entry), p.max_leverage)
        ret_pct = notional_frac * pnl_ps / entry * 100
        trades.append(
            Trade(
                date=str(d),
                side=side,
                entry_time=ts.strftime("%H:%M"),
                entry=round(entry, 4),
                stop=round(stop, 4),
                exit_time=exit_ts.strftime("%H:%M"),
                exit=round(exit_px, 4),
                exit_reason=reason,
                r_multiple=round(r_mult, 4),
                ret_pct=round(ret_pct, 4),
                rvol=round(float(rv), 3),
                clv=round(float(clv), 3),
            )
        )
    return trades


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def metrics(trades: list[Trade], n_days: int | None = None) -> dict:
    if not trades:
        return {"trades": 0}
    r = np.array([t.r_multiple for t in trades])
    rets = np.array([t.ret_pct for t in trades]) / 100
    eq = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(eq)
    dd = (eq / peak - 1).min()
    wins, losses = r[r > 0], r[r <= 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
    dates = pd.to_datetime([t.date for t in trades])
    years = max((dates[-1] - dates[0]).days / 365.25, 1e-9)
    cagr = eq[-1] ** (1 / years) - 1
    # daily-return Sharpe including flat days
    daily = pd.Series(rets, index=dates).groupby(level=0).sum()
    if n_days:
        bdays = pd.bdate_range(dates[0], dates[-1])
        daily = daily.reindex(bdays, fill_value=0.0)
    sharpe = daily.mean() / daily.std() * math.sqrt(252) if daily.std() > 0 else 0.0
    return {
        "trades": int(len(r)),
        "win_rate": round(float((r > 0).mean()), 4),
        "avg_r": round(float(r.mean()), 4),
        "avg_win_r": round(float(wins.mean()), 3) if len(wins) else 0.0,
        "avg_loss_r": round(float(losses.mean()), 3) if len(losses) else 0.0,
        "profit_factor": round(float(pf), 3),
        "total_return_pct": round(float((eq[-1] - 1) * 100), 2),
        "cagr_pct": round(float(cagr * 100), 2),
        "max_dd_pct": round(float(dd * 100), 2),
        "sharpe": round(float(sharpe), 2),
        "long_trades": int(sum(t.side == 1 for t in trades)),
        "short_trades": int(sum(t.side == -1 for t in trades)),
    }


def by_period(trades: list[Trade], freq: str = "Y") -> dict:
    out = {}
    for t in trades:
        key = t.date[:4] if freq == "Y" else f"{t.date[:4]}-Q{(int(t.date[5:7]) - 1) // 3 + 1}"
        out.setdefault(key, []).append(t)
    return {k: metrics(v) for k, v in sorted(out.items())}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--symbol", default="QQQ")
    ap.add_argument("--source", choices=["yahoo", "alpaca", "csv"], default="yahoo")
    ap.add_argument("--csv")
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--timeframe", default="1Min", help="alpaca timeframe")
    ap.add_argument("--bar-minutes", type=int, default=0, help="resample to N-minute bars")
    for f in Params.__dataclass_fields__.values():
        flag = "--" + f.name.replace("_", "-")
        if f.type in ("bool", bool):
            ap.add_argument(
                flag, type=lambda s: s.lower() in ("1", "true", "yes"), default=f.default
            )
        else:
            typ = {"int": int, "float": float}.get(
                f.type if isinstance(f.type, str) else f.type.__name__, str
            )
            ap.add_argument(flag, type=typ, default=f.default)
    ap.add_argument("--output-dir", default="reports/")
    args = ap.parse_args(argv)

    if args.source == "yahoo":
        df = load_yahoo(args.symbol)
    elif args.source == "alpaca":
        end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        df = load_alpaca(args.symbol, args.start, end, args.timeframe, Path(".cache"))
    else:
        df = load_csv(args.csv)
    if args.bar_minutes:
        df = resample(df, args.bar_minutes)
    p = Params(**{k: getattr(args, k) for k in Params.__dataclass_fields__})
    garch = None
    if p.garch_filter != "none":
        garch = garch_forecast(load_yahoo_daily(args.symbol)["close"])
    trades = run_backtest(df, p, garch)
    res = {
        "symbol": args.symbol,
        "params": asdict(p),
        "label": p.label(),
        "overall": metrics(trades),
        "by_year": by_period(trades),
    }
    print(json.dumps(res, indent=2))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([asdict(t) for t in trades]).to_csv(
        out / f"ivb_trades_{args.symbol}.csv", index=False
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
