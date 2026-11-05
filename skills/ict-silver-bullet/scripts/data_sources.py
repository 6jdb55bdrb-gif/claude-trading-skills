"""Intraday OHLC loaders for the Silver Bullet backtester.

Sources (all keyless):

* ``binance:<PAIR>`` -- Binance public market-data mirror
  (``data-api.binance.vision``), years of 1m/5m/15m crypto klines.
* ``yahoo:<TICKER>`` -- Yahoo Finance chart API via ``yfinance`` (optional
  dependency). Intraday history is limited by Yahoo: 1m ~30 days, 2m/5m/15m
  ~60 days. Pre/post-market bars are included so the pre-window liquidity
  range is complete for ETFs.
* ``csv:<path>`` -- any local CSV with a timestamp column (UTC unless it
  carries an offset) plus open/high/low/close.

Downloaded frames are cached as CSV under ``--cache-dir`` so repeated runs are
reproducible and offline.
"""

from __future__ import annotations

import hashlib
import sys
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

try:  # optional: only yahoo: sources need yfinance
    import yfinance as yf

    HAS_YFINANCE = True
except ImportError:  # degraded path: binance:/csv: sources still work
    yf = None
    HAS_YFINANCE = False

BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
BINANCE_INTERVALS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
}
YAHOO_MAX_DAYS = {"1m": 29, "2m": 59, "5m": 59, "15m": 59, "30m": 59, "60m": 729, "1h": 729}


def parse_source(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise ValueError(
            f"source must look like 'binance:BTCUSDT', 'yahoo:SPY' or 'csv:path' (got {spec!r})"
        )
    kind, ident = spec.split(":", 1)
    kind = kind.lower()
    if kind not in ("binance", "yahoo", "csv") or not ident:
        raise ValueError(f"unsupported source {spec!r}")
    return kind, ident


def load_bars(
    spec: str, interval: str, days: int, cache_dir: Path | None = None, end: datetime | None = None
) -> pd.DataFrame:
    kind, ident = parse_source(spec)
    if kind == "csv":
        return load_csv(Path(ident))
    end = end or datetime.now(timezone.utc).replace(second=0, microsecond=0)
    cache_file = None
    if cache_dir is not None:
        key = hashlib.sha1(f"{spec}|{interval}|{days}|{end:%Y-%m-%d}".encode()).hexdigest()[:12]
        cache_file = (
            Path(cache_dir)
            / f"{kind}_{ident.replace('=', '').replace('^', '')}_{interval}_{days}d_{key}.csv"
        )
        if cache_file.exists():
            return load_csv(cache_file)
    if kind == "binance":
        df = fetch_binance(ident, interval, end - timedelta(days=days), end)
    else:
        df = fetch_yahoo(ident, interval, days)
    if cache_file is not None and not df.empty:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache_file, index_label="timestamp")
    return df


def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    ts_col = next((cols[k] for k in ("timestamp", "datetime", "date", "time") if k in cols), None)
    if ts_col is None:
        raise ValueError(f"{path}: no timestamp/datetime column")
    idx = pd.to_datetime(df[ts_col], utc=True)
    out = df.drop(columns=[ts_col]).rename(columns=str.lower)
    out.index = pd.DatetimeIndex(idx)
    return out[["open", "high", "low", "close"]].astype(float)


def fetch_binance(
    symbol: str, interval: str, start: datetime, end: datetime, session=None
) -> pd.DataFrame:
    import requests

    if interval not in BINANCE_INTERVALS:
        raise ValueError(f"binance interval must be one of {sorted(BINANCE_INTERVALS)}")
    sess = session or requests.Session()
    step = BINANCE_INTERVALS[interval]
    cursor = int(start.timestamp() * 1000)
    stop = int(end.timestamp() * 1000)
    rows: list[list] = []
    while cursor < stop:
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "startTime": cursor,
            "endTime": stop,
            "limit": 1000,
        }
        for attempt in range(5):
            try:
                resp = sess.get(BINANCE_URL, params=params, timeout=30)
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                resp.raise_for_status()
                batch = resp.json()
                break
            except Exception as exc:  # network / rate limit -> backoff
                if attempt == 4:
                    raise RuntimeError(f"binance fetch failed: {exc}") from exc
                _time.sleep(2**attempt)
        if not batch:
            break
        rows.extend(batch)
        cursor = int(batch[-1][0]) + step
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close"])
    df = pd.DataFrame([r[:5] for r in rows], columns=["ts", "open", "high", "low", "close"])
    df.index = pd.to_datetime(df.pop("ts"), unit="ms", utc=True)
    df = df.astype(float)
    return df[~df.index.duplicated()].sort_index()


def fetch_yahoo(ticker: str, interval: str, days: int) -> pd.DataFrame:
    if not HAS_YFINANCE:
        print(
            "yfinance is required for yahoo: sources (pip install -r requirements.txt)",
            file=sys.stderr,
        )
        raise SystemExit(2)
    max_days = YAHOO_MAX_DAYS.get(interval)
    if max_days is None:
        raise ValueError(f"yahoo interval must be one of {sorted(YAHOO_MAX_DAYS)}")
    days = min(days, max_days)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    chunk = timedelta(days=7 if interval == "1m" else days)
    frames = []
    cur = start
    while cur < end:
        nxt = min(cur + chunk, end)
        part = yf.download(
            ticker,
            start=cur,
            end=nxt,
            interval=interval,
            prepost=True,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if part is not None and not part.empty:
            if isinstance(part.columns, pd.MultiIndex):
                part.columns = part.columns.get_level_values(0)
            frames.append(part)
        cur = nxt
    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close"])
    df = pd.concat(frames).rename(columns=str.lower)[["open", "high", "low", "close"]]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("UTC")
    df = df[~df.index.duplicated(keep="last")].sort_index().dropna()
    return df.astype(float)
