"""Stochastic oscillator, MACD and simple moving average."""

from __future__ import annotations

import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def stochastic(high, low, close, k_period: int = 14, smooth_k: int = 3, d_period: int = 3):
    """Full stochastic (14,3,3 by default). Returns (%K, %D). Flat ranges read 50."""
    hh = high.rolling(k_period).max()
    ll = low.rolling(k_period).min()
    rng = hh - ll
    raw = ((close - ll) / rng.where(rng > 0) * 100).where(rng > 0, 50.0).where(hh.notna())
    k = raw.rolling(smooth_k).mean()
    d = k.rolling(d_period).mean()
    return k, d


def macd(close, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (MACD line, signal line, histogram)."""
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def add_indicators(
    df: pd.DataFrame, ma: int = 50, stoch=(14, 3, 3), macd_p=(12, 26, 9)
) -> pd.DataFrame:
    out = df.copy()
    out[f"sma{ma}"] = sma(out["close"], ma)
    out["stoch_k"], out["stoch_d"] = stochastic(out["high"], out["low"], out["close"], *stoch)
    out["macd"], out["macd_signal"], out["macd_hist"] = macd(out["close"], *macd_p)
    return out
