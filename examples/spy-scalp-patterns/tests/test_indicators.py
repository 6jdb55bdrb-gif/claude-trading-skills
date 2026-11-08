"""Tests for Stochastic, MACD and SMA indicators."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from indicators import add_indicators, macd, sma, stochastic  # noqa: E402


def test_sma():
    s = pd.Series([1.0, 2, 3, 4, 5])
    out = sma(s, 3)
    assert out.isna().sum() == 2
    assert list(out.iloc[2:]) == [2.0, 3.0, 4.0]


def test_stochastic_raw_and_smoothed():
    # 3-bar lookback, no smoothing: %K = (C - LL) / (HH - LL) * 100
    high = pd.Series([10.0, 11, 12, 13, 14])
    low = pd.Series([8.0, 9, 10, 11, 12])
    close = pd.Series([9.0, 10, 11, 12, 13])
    k, d = stochastic(high, low, close, k_period=3, smooth_k=1, d_period=1)
    # bar 2: HH=12, LL=8 -> (11-8)/4 = 75
    assert k.iloc[2] == pytest.approx(75.0)
    assert d.iloc[2] == pytest.approx(75.0)
    k3, d3 = stochastic(high, low, close, k_period=3, smooth_k=2, d_period=2)
    # raw K: [nan, nan, 75, 75, 75] -> smoothed K bar3 = 75; D bar4 = 75
    assert k3.iloc[3] == pytest.approx(75.0) and d3.iloc[4] == pytest.approx(75.0)


def test_stochastic_flat_range_is_neutral():
    flat = pd.Series([5.0] * 20)
    k, d = stochastic(flat, flat, flat)
    assert k.dropna().eq(50).all()


def test_macd_matches_manual_ema():
    close = pd.Series(np.linspace(100, 110, 60))
    line, signal, hist = macd(close, 12, 26, 9)
    ema = lambda s, n: s.ewm(span=n, adjust=False).mean()  # noqa: E731
    exp_line = ema(close, 12) - ema(close, 26)
    assert line.iloc[-1] == pytest.approx(exp_line.iloc[-1])
    assert signal.iloc[-1] == pytest.approx(ema(exp_line, 9).iloc[-1])
    assert hist.iloc[-1] == pytest.approx(line.iloc[-1] - signal.iloc[-1])
    assert line.iloc[-1] > 0  # rising series -> positive MACD


def test_add_indicators_columns():
    idx = pd.date_range("2026-01-05 09:30", periods=120, freq="5min", tz="America/New_York")
    c = pd.Series(np.sin(np.arange(120) / 5) + 100, index=idx)
    df = pd.DataFrame({"open": c, "high": c + 0.1, "low": c - 0.1, "close": c, "volume": 1})
    out = add_indicators(df)
    for col in ["sma50", "stoch_k", "stoch_d", "macd", "macd_signal", "macd_hist"]:
        assert col in out
    assert out["sma50"].iloc[49] == pytest.approx(c.iloc[:50].mean())
