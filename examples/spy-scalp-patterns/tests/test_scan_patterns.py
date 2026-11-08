"""Tests for pattern labelling and forward returns."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scan_patterns import (  # noqa: E402
    crosses_above,
    crosses_below,
    events,
    forward_returns,
    summarize,
)


def _bars(closes, start="2026-01-05 09:30", freq="5min"):
    idx = pd.date_range(start, periods=len(closes), freq=freq, tz="America/New_York")
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1})


def test_crosses():
    a = pd.Series([1, 2, 3, 2, 1.0])
    b = pd.Series([2, 2, 2, 2, 2.0])
    assert list(crosses_above(a, b)) == [False, False, True, False, False]
    assert list(crosses_below(a, b)) == [False, False, False, False, True]


def test_forward_returns_enter_next_open_and_stay_in_session():
    d1 = _bars([100, 101, 102, 103])
    d2 = _bars([200, 210, 220, 230], start="2026-01-06 09:30")
    df = pd.concat([d1, d2])
    df.loc[df.index[1], "open"] = 100.5
    fwd = forward_returns(df, horizons=[1, 2])
    # bar0 signal: enter bar1 open 100.5, exit bar1 close 101 (h=1)
    assert fwd["fwd_1"].iloc[0] == pytest.approx((101 / 100.5 - 1) * 1e4)
    # bar0, h=2: exit at bar2 close
    assert fwd["fwd_2"].iloc[0] == pytest.approx((102 / 100.5 - 1) * 1e4)
    # bar2, h=2 would need bar4 (next day) -> NaN; last bar of day -> NaN
    assert np.isnan(fwd["fwd_2"].iloc[2]) and np.isnan(fwd["fwd_1"].iloc[3])


def test_events_have_no_lookahead():
    rng = np.random.default_rng(0)
    df = _bars(100 + np.cumsum(rng.normal(0, 0.2, 300)))
    full = events(df)
    cut = events(df.iloc[:200])
    # signals up to bar 199 must not change when future bars are removed
    pd.testing.assert_frame_equal(full.iloc[:200], cut)


def test_summarize_is_oos_split():
    idx = pd.to_datetime(
        ["2024-06-03 10:00", "2024-06-04 10:00", "2025-06-03 10:00", "2025-06-04 10:00"]
    ).tz_localize("America/New_York")
    fwd = pd.Series([2.0, 4.0, -1.0, -3.0], index=idx)
    mask = pd.Series(True, index=idx)
    r = summarize(mask, fwd, split="2025-01-01")
    assert r["n_is"] == 2 and r["mean_is"] == pytest.approx(3.0)
    assert r["n_oos"] == 2 and r["mean_oos"] == pytest.approx(-2.0)
    assert r["hit_is"] == pytest.approx(100.0) and r["hit_oos"] == pytest.approx(0.0)
