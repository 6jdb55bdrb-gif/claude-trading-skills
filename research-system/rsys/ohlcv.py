"""DATA ENGINEER: historical OHLCV via ccxt -> canonical CSV (shared by every engine).

One canonical dataset keeps the engine cross-check honest: freqtrade, jesse, nautilus and
FinRL all read candles exported from the same CSV files.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def make_exchange(name: str):
    import ccxt  # imported lazily so pure helpers work without ccxt

    # requests_trust_env: honour HTTPS_PROXY / REQUESTS_CA_BUNDLE like any other HTTP client.
    exchange = getattr(ccxt, name)({"enableRateLimit": True, "requests_trust_env": True})
    exchange.load_markets()
    return exchange


def _fetch_with_retry(exchange, pair, timeframe, since, limit, retries=4):
    for attempt in range(retries + 1):
        try:
            return exchange.fetch_ohlcv(pair, timeframe, since=since, limit=limit)
        except Exception as exc:
            # ccxt.NetworkError covers timeouts and RateLimitExceeded; anything else is fatal.
            retryable = any(cls.__name__ == "NetworkError" for cls in type(exc).__mro__)
            if attempt == retries or not retryable:
                raise
            time.sleep(2 ** (attempt + 1))
    return []


def first_candle_ms(exchange, pair: str, start_ms: int) -> int | None:
    rows = _fetch_with_retry(exchange, pair, "1d", since=start_ms, limit=3)
    return rows[0][0] if rows else None


def download(
    exchange, pair: str, timeframe: str, start_ms: int, end_ms: int | None, limit: int = 100
) -> pd.DataFrame:
    """Page forward from start_ms. Drops duplicates and the still-open last candle."""
    step = exchange.parse_timeframe(timeframe) * 1000
    now = exchange.milliseconds()
    stop = min(end_ms, now) if end_ms else now
    rows, since = [], start_ms
    while since < stop:
        batch = _fetch_with_retry(exchange, pair, timeframe, since=since, limit=limit)
        if not batch:
            break
        rows.extend(batch)
        last = batch[-1][0]
        if last + step <= since:
            break
        since = last + step
    df = pd.DataFrame(rows, columns=COLUMNS)
    if df.empty:
        return df
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    df = df[(df["timestamp"] + step <= now) & (df["timestamp"] < stop)]
    df = df.astype({"timestamp": "int64"} | {c: "float64" for c in COLUMNS[1:]})
    return df.reset_index(drop=True)


def validate(df: pd.DataFrame, timeframe: str) -> dict:
    step = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14_400, "1d": 86_400}[timeframe]
    diffs = df["timestamp"].diff().dropna() // (step * 1000)
    gaps = diffs[diffs > 1]
    bad = (
        (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
    )
    report = {
        "rows": int(len(df)),
        "start": _iso(df["timestamp"].iloc[0]) if len(df) else None,
        "end": _iso(df["timestamp"].iloc[-1]) if len(df) else None,
        "gaps": int(len(gaps)),
        "missing_candles": int((gaps - 1).sum()),
        "duplicates": int(df["timestamp"].duplicated().sum()),
        "bad_price_rows": int(bad.sum()),
        "zero_volume_rows": int((df["volume"] <= 0).sum()),
    }
    report["ok"] = (
        report["duplicates"] == 0
        and report["bad_price_rows"] == 0
        and (report["missing_candles"] <= max(1, len(df) // 1000))
    )
    return report


def _iso(ms) -> str:
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").isoformat()


def _stem(pair: str, timeframe: str) -> str:
    return f"{pair.replace('/', '_')}-{timeframe}"


def save_csv(df: pd.DataFrame, root: Path, exchange: str, pair: str, timeframe: str) -> Path:
    path = Path(root) / exchange / f"{_stem(pair, timeframe)}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"timestamp": "int64"} | {c: "float64" for c in COLUMNS[1:]})


def export_freqtrade(df: pd.DataFrame, datadir: Path, pair: str, timeframe: str) -> Path:
    """freqtrade 'json' OHLCV format: [[ms, open, high, low, close, volume], ...]."""
    path = Path(datadir) / f"{_stem(pair, timeframe)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [[int(r[0]), *map(float, r[1:])] for r in df[COLUMNS].itertuples(index=False)]
    path.write_text(json.dumps(rows))
    return path
