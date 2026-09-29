"""Shared indicators (pure numpy/pandas) so every engine computes identical signals."""

from __future__ import annotations

import numpy as np
import pandas as pd


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Wilder ATR (RMA of true range), seeded with the SMA of the first `period` values."""
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(
        axis=1
    )
    tr.iloc[0] = high.iloc[0] - low.iloc[0]
    out = np.full(len(tr), np.nan)
    if len(tr) >= period:
        out[period - 1] = tr.iloc[:period].mean()
        values = tr.to_numpy()
        for i in range(period, len(tr)):
            out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return pd.Series(out, index=close.index)


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """Classic SuperTrend. Returns columns supertrend, st_direction (1 up / -1 down).

    Each row only uses data up to and including that row's close (no look-ahead);
    engines must act on the NEXT candle.
    """
    high, low, close = df["high"], df["low"], df["close"]
    a = atr(high, low, close, period).to_numpy()
    hl2 = ((high + low) / 2).to_numpy()
    c = close.to_numpy()
    n = len(df)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    line = np.full(n, np.nan)
    direction = np.zeros(n, dtype=int)
    for i in range(n):
        if np.isnan(a[i]):
            continue
        basic_upper = hl2[i] + multiplier * a[i]
        basic_lower = hl2[i] - multiplier * a[i]
        if i == 0 or np.isnan(upper[i - 1]):
            upper[i], lower[i] = basic_upper, basic_lower
            direction[i] = 1 if c[i] > basic_upper else -1
            line[i] = lower[i] if direction[i] == 1 else upper[i]
            continue
        upper[i] = (
            basic_upper if basic_upper < upper[i - 1] or c[i - 1] > upper[i - 1] else upper[i - 1]
        )
        lower[i] = (
            basic_lower if basic_lower > lower[i - 1] or c[i - 1] < lower[i - 1] else lower[i - 1]
        )
        if direction[i - 1] == -1:
            direction[i] = 1 if c[i] > upper[i] else -1
        else:
            direction[i] = -1 if c[i] < lower[i] else 1
        line[i] = lower[i] if direction[i] == 1 else upper[i]
    return pd.DataFrame({"supertrend": line, "st_direction": direction}, index=df.index)
