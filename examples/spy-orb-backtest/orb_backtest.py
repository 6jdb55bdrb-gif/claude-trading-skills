#!/usr/bin/env python3
"""SPY 30-minute Opening Range Breakout (ORB) backtester on 5-minute candles.

Rules (defaults):
  * Opening range = high/low of the first 30 minutes of the regular session
    (09:30-10:00 ET, i.e. the first six 5-minute candles).
  * From 10:00 ET onward, the first 5-minute candle that CLOSES above the range
    high goes long; the first that closes below the range low goes short.
    One trade per day.
  * Entry at the close of the breakout candle (or the next candle's open with
    --entry-mode next_open).
  * Fixed $1,000 position on every trade (fractional shares), no compounding.
  * Stop loss = 5% of the trade (entry * 0.95 long / entry * 1.05 short),
    checked intrabar against high/low.
  * Optional take-profit; otherwise exit at the close of the last candle of
    the day (15:55 ET bar).

Data: yfinance 5-minute bars (Yahoo only serves the last ~60 days) or a CSV
with timestamp, open, high, low, close[, volume] columns for longer history.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    print("pandas is required: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)

TZ = "America/New_York"


@dataclass
class ORBConfig:
    range_minutes: int = 30
    position_size: float = 1000.0
    stop_pct: float = 5.0
    stop_mode: str = "pct"  # "pct" = stop_pct from entry; "range" = opposite side of range
    take_profit_pct: float | None = None
    entry_mode: str = "close"  # "close" = breakout candle close; "next_open"
    allow_short: bool = True
    last_entry_time: str = "15:30"  # no new entries after this bar start (ET)
    commission: float = 0.0  # per side, dollars
    slippage_pct: float = 0.0  # per side, % of price


# --------------------------------------------------------------------------- data


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case OHLCV columns, tz-convert to ET, keep regular session only."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    df = df[[c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]]
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx
    df.index = idx.tz_convert(TZ)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df.between_time("09:30", "15:55").dropna(subset=["open", "high", "low", "close"])


def load_yfinance(symbol: str, period: str) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        print(
            "yfinance is required for downloads: pip install -r requirements.txt", file=sys.stderr
        )
        sys.exit(2)
    df = yf.download(
        symbol, period=period, interval="5m", prepost=False, progress=False, auto_adjust=False
    )
    if df.empty:
        raise SystemExit(f"No data returned for {symbol}")
    return normalize(df)


def load_csv(path: str, assume_tz: str = TZ) -> pd.DataFrame:
    raw = pd.read_csv(path)
    ts_col = next(c for c in raw.columns if c.lower() in ("timestamp", "datetime", "date", "time"))
    idx = pd.to_datetime(raw[ts_col])
    if idx.dt.tz is None:
        idx = idx.dt.tz_localize(assume_tz)
    raw.index = pd.DatetimeIndex(idx)
    return normalize(raw.drop(columns=[ts_col]))


# ----------------------------------------------------------------------- strategy


def opening_range(day: pd.DataFrame, minutes: int = 30):
    """Return (range_high, range_low, bars_after_range) for one session."""
    start = day.index[0].normalize() + pd.Timedelta(hours=9, minutes=30)
    end = start + pd.Timedelta(minutes=minutes)
    rng = day[(day.index >= start) & (day.index < end)]
    after = day[day.index >= end]
    if rng.empty:
        return None, None, after
    return float(rng["high"].max()), float(rng["low"].min()), after


def _fill(price: float, side: int, cfg: ORBConfig) -> float:
    """Apply slippage: side=+1 buying, -1 selling."""
    return price * (1 + side * cfg.slippage_pct / 100)


def simulate_day(day: pd.DataFrame, cfg: ORBConfig) -> dict | None:
    """Simulate at most one ORB trade for a single session. None = no trade."""
    hi, lo, after = opening_range(day, cfg.range_minutes)
    if hi is None or after.empty:
        return None
    cutoff = pd.Timestamp(cfg.last_entry_time).time()

    bars = after.reset_index()
    ts_col = bars.columns[0]
    for i, bar in bars.iterrows():
        if bar[ts_col].time() > cutoff:
            return None
        if bar["close"] > hi:
            direction = 1
        elif bar["close"] < lo and cfg.allow_short:
            direction = -1
        else:
            continue

        if cfg.entry_mode == "next_open":
            if i + 1 >= len(bars):
                return None
            entry_idx, raw_entry, first_check = i + 1, float(bars.loc[i + 1, "open"]), i + 1
        else:
            entry_idx, raw_entry, first_check = i, float(bar["close"]), i + 1
        entry = _fill(raw_entry, direction, cfg)
        return _manage(bars, ts_col, entry_idx, first_check, entry, direction, hi, lo, cfg)
    return None


def _manage(bars, ts_col, entry_idx, first_check, entry, direction, hi, lo, cfg) -> dict:
    if cfg.stop_mode == "range":
        stop = lo if direction == 1 else hi
    else:
        stop = entry * (1 - direction * cfg.stop_pct / 100)
    target = None
    if cfg.take_profit_pct:
        target = entry * (1 + direction * cfg.take_profit_pct / 100)

    exit_price, exit_reason, exit_time = None, "eod", None
    for j in range(first_check, len(bars)):
        b = bars.loc[j]
        # Gap through the stop on the bar open -> fill at the open.
        if direction == 1:
            stop_hit = b["low"] <= stop
            stop_px = min(stop, b["open"])
            tgt_hit = target is not None and b["high"] >= target
            tgt_px = max(target, b["open"]) if target else None
        else:
            stop_hit = b["high"] >= stop
            stop_px = max(stop, b["open"])
            tgt_hit = target is not None and b["low"] <= target
            tgt_px = min(target, b["open"]) if target else None
        # Same-bar stop & target: assume the stop came first (conservative).
        if stop_hit:
            exit_price, exit_reason, exit_time = stop_px, "stop", b[ts_col]
            break
        if tgt_hit:
            exit_price, exit_reason, exit_time = tgt_px, "target", b[ts_col]
            break
    if exit_price is None:
        last = bars.iloc[-1]
        exit_price, exit_time = float(last["close"]), last[ts_col]

    exit_price = _fill(float(exit_price), -direction, cfg)
    shares = cfg.position_size / entry
    gross = shares * (exit_price - entry) * direction
    pnl = gross - 2 * cfg.commission
    entry_time = bars.loc[entry_idx, ts_col]
    return {
        "date": entry_time.date().isoformat(),
        "direction": "long" if direction == 1 else "short",
        "range_high": hi,
        "range_low": lo,
        "entry_time": entry_time.strftime("%H:%M"),
        "entry_price": entry,
        "stop_price": stop,
        "target_price": target,
        "exit_time": pd.Timestamp(exit_time).strftime("%H:%M"),
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "shares": shares,
        "position_value": cfg.position_size,
        "pnl": pnl,
        "return_pct": pnl / cfg.position_size * 100,
    }


def backtest(df: pd.DataFrame, cfg: ORBConfig) -> pd.DataFrame:
    trades = []
    for _, day in df.groupby(df.index.date):
        t = simulate_day(day, cfg)
        if t:
            trades.append(t)
    return pd.DataFrame(trades)


# ------------------------------------------------------------------------ metrics


def compute_metrics(trades: pd.DataFrame, cfg: ORBConfig, num_days: int | None = None) -> dict:
    if trades.empty:
        return {"num_trades": 0, "trading_days": num_days}
    pnl = trades["pnl"]
    equity = cfg.position_size + pnl.cumsum()
    peak = equity.cummax().clip(lower=cfg.position_size)
    dd = equity - peak
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_loss = -losses.sum()
    by_dir = {
        d: {
            "trades": int(len(g)),
            "win_rate_pct": round(float((g["pnl"] > 0).mean() * 100), 2),
            "pnl": round(float(g["pnl"].sum()), 2),
        }
        for d, g in trades.groupby("direction")
    }
    std = pnl.std(ddof=1) if len(pnl) > 1 else 0.0
    return {
        "trading_days": num_days,
        "num_trades": int(len(trades)),
        "win_rate_pct": round(float((pnl > 0).mean() * 100), 2),
        "total_pnl": round(float(pnl.sum()), 2),
        "total_return_on_1000_pct": round(float(pnl.sum() / cfg.position_size * 100), 2),
        "avg_pnl_per_trade": round(float(pnl.mean()), 2),
        "avg_win": round(float(wins.mean()), 2) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) else 0.0,
        "largest_win": round(float(pnl.max()), 2),
        "largest_loss": round(float(pnl.min()), 2),
        "profit_factor": round(float(wins.sum() / gross_loss), 2) if gross_loss > 0 else None,
        "max_drawdown": round(float(dd.min()), 2),
        "sharpe_per_trade_annualized": round(float(pnl.mean() / std * (252**0.5)), 2)
        if std
        else None,
        "final_equity": round(float(equity.iloc[-1]), 2),
        "exit_reasons": {k: int(v) for k, v in trades["exit_reason"].value_counts().items()},
        "by_direction": by_dir,
    }


# ------------------------------------------------------------------------- report


def write_reports(trades, metrics, cfg, meta, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    base = out_dir / f"spy_orb_backtest_{stamp}"
    trades.to_csv(f"{base}_trades.csv", index=False)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": asdict(cfg),
        **meta,
        "metrics": metrics,
    }
    Path(f"{base}.json").write_text(json.dumps(payload, indent=2, default=str))

    m = metrics
    lines = [
        f"# SPY {cfg.range_minutes}-Minute Opening Range Breakout Backtest",
        "",
        f"**Generated:** {payload['generated_at']}  ",
        f"**Data:** {meta['source']} | {meta['start']} to {meta['end']} ({m.get('trading_days')} sessions)  ",
        f"**Rules:** {cfg.range_minutes}-min range, 5-min close breakout, entry={cfg.entry_mode}, "
        f"stop={f'{cfg.stop_pct:.1f}% of trade' if cfg.stop_mode == 'pct' else 'opposite side of range'}, "
        f"target={f'{cfg.take_profit_pct:.1f}%' if cfg.take_profit_pct else 'none (exit at close)'}, "
        f"${cfg.position_size:,.0f} per trade",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    if m["num_trades"] == 0:
        lines.append("| Trades | 0 |")
    else:
        pf = m["profit_factor"] if m["profit_factor"] is not None else "n/a"
        lines += [
            f"| Trades | {m['num_trades']} |",
            f"| Win rate | {m['win_rate_pct']}% |",
            f"| Total P&L | ${m['total_pnl']:,.2f} ({m['total_return_on_1000_pct']}% of $1,000) |",
            f"| Final equity | ${m['final_equity']:,.2f} |",
            f"| Avg P&L / trade | ${m['avg_pnl_per_trade']:,.2f} |",
            f"| Avg win / avg loss | ${m['avg_win']:,.2f} / ${m['avg_loss']:,.2f} |",
            f"| Largest win / loss | ${m['largest_win']:,.2f} / ${m['largest_loss']:,.2f} |",
            f"| Profit factor | {pf} |",
            f"| Max drawdown | ${m['max_drawdown']:,.2f} |",
            f"| Exit reasons | {', '.join(f'{k}: {v}' for k, v in m['exit_reasons'].items())} |",
        ]
        for d, s in m["by_direction"].items():
            lines.append(
                f"| {d.title()} trades | {s['trades']} trades, {s['win_rate_pct']}% win, ${s['pnl']:,.2f} |"
            )
        lines += [
            "",
            "## Trades",
            "",
            "| Date | Dir | Entry | Price | Exit | Price | Reason | P&L |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for t in trades.itertuples():
            lines.append(
                f"| {t.date} | {t.direction} | {t.entry_time} | {t.entry_price:.2f} | {t.exit_time} | "
                f"{t.exit_price:.2f} | {t.exit_reason} | {t.pnl:+.2f} |"
            )
    lines += [
        "",
        "_Backtest results are hypothetical and exclude real-world fills, fees and taxes unless configured._",
        "",
    ]
    Path(f"{base}.md").write_text("\n".join(lines))
    return {"markdown": f"{base}.md", "json": f"{base}.json", "trades_csv": f"{base}_trades.csv"}


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--symbol", default="SPY")
    p.add_argument("--period", default="60d", help="yfinance period (5-min data max ~60d)")
    p.add_argument("--csv", help="Local 5-min OHLCV CSV instead of yfinance")
    p.add_argument("--range-minutes", type=int, default=30)
    p.add_argument("--position-size", type=float, default=1000.0)
    p.add_argument("--stop-pct", type=float, default=5.0)
    p.add_argument("--stop-mode", choices=["pct", "range"], default="pct")
    p.add_argument("--take-profit-pct", type=float)
    p.add_argument("--entry-mode", choices=["close", "next_open"], default="close")
    p.add_argument("--long-only", action="store_true")
    p.add_argument("--commission", type=float, default=0.0)
    p.add_argument("--slippage-pct", type=float, default=0.0)
    p.add_argument("--output-dir", default="reports/")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    cfg = ORBConfig(
        range_minutes=a.range_minutes,
        position_size=a.position_size,
        stop_pct=a.stop_pct,
        stop_mode=a.stop_mode,
        take_profit_pct=a.take_profit_pct,
        entry_mode=a.entry_mode,
        allow_short=not a.long_only,
        commission=a.commission,
        slippage_pct=a.slippage_pct,
    )
    df = load_csv(a.csv) if a.csv else load_yfinance(a.symbol, a.period)
    source = a.csv or f"yfinance {a.symbol} 5m ({a.period})"
    num_days = len(set(df.index.date))
    trades = backtest(df, cfg)
    metrics = compute_metrics(trades, cfg, num_days)
    meta = {"source": source, "start": str(df.index[0].date()), "end": str(df.index[-1].date())}
    paths = write_reports(trades, metrics, cfg, meta, Path(a.output_dir))
    print(json.dumps({"metrics": metrics, "reports": paths}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
