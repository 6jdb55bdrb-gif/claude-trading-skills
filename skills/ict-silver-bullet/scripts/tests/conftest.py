"""Shared fixtures for ict-silver-bullet tests."""

import os
import sys

import pandas as pd
import pytest

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DAY = "2026-03-04"  # a Wednesday


def _bars(day=DAY, overrides=None, after=None):
    """1-minute NY bars 08:00-12:30, flat ~100 with a 106 high at 08:30.

    ``overrides`` maps "HH:MM" -> (open, high, low, close).
    ``after`` is a default bar for every minute >= 10:03 that is not overridden.
    """
    idx = pd.date_range(f"{day} 08:00", f"{day} 12:30", freq="1min", tz="America/New_York")
    rows = []
    for ts in idx:
        hhmm = ts.strftime("%H:%M")
        bar = (100.0, 100.2, 99.8, 100.0)
        if hhmm == "08:30":
            bar = (100.0, 106.0, 99.9, 100.0)
        if after is not None and hhmm >= "10:03":
            bar = after
        if overrides and hhmm in overrides:
            bar = overrides[hhmm]
        rows.append(bar)
    return pd.DataFrame(rows, index=idx.tz_convert("UTC"), columns=["open", "high", "low", "close"])


# A canonical bullish Silver Bullet in the AM window:
#   10:00 sweeps the 99.8 pre-window low to 98.5
#   10:01 displacement candle 99 -> 101.5 (closes above the 100.2 swing high = MSS)
#   10:02 low 100.5 > 10:00 high 99.2 -> bullish FVG [99.2, 100.5]
BULL_CORE = {
    "10:00": (99.5, 99.2, 98.5, 99.0),
    "10:01": (99.0, 101.6, 98.9, 101.5),
    "10:02": (101.5, 102.0, 100.5, 101.8),
}


@pytest.fixture
def bars_factory():
    return _bars


@pytest.fixture
def bull_core():
    return dict(BULL_CORE)


def mirror(df, pivot=200.0):
    """Reflect prices around ``pivot`` to turn a bullish path into a bearish one."""
    out = pd.DataFrame(index=df.index)
    out["open"] = pivot - df["open"]
    out["close"] = pivot - df["close"]
    out["high"] = pivot - df["low"]
    out["low"] = pivot - df["high"]
    return out


@pytest.fixture
def mirror_fn():
    return mirror
