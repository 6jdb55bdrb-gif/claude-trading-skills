import numpy as np
import pandas as pd
from rsys.indicators import atr, supertrend


def _frame(closes):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame(
        {"open": closes, "high": closes * 1.01, "low": closes * 0.99, "close": closes}
    )


def test_atr_seed_is_sma_of_true_range():
    df = _frame([100.0] * 20)
    out = atr(df["high"], df["low"], df["close"], 5)
    assert out.iloc[:4].isna().all()
    assert np.isclose(out.iloc[4], 2.0)
    assert np.isclose(out.iloc[-1], 2.0)


def test_direction_follows_trend():
    up = _frame(np.linspace(100, 200, 120))
    down = _frame(np.linspace(200, 100, 120))
    assert supertrend(up, 10, 3.0)["st_direction"].iloc[-1] == 1
    assert supertrend(down, 10, 3.0)["st_direction"].iloc[-1] == -1


def test_flips_after_reversal():
    prices = np.concatenate([np.linspace(100, 200, 80), np.linspace(200, 120, 80)])
    st = supertrend(_frame(prices), 10, 3.0)["st_direction"]
    assert (st.iloc[20:80] == 1).all()
    assert st.iloc[-1] == -1
    assert ((st.shift(1) == 1) & (st == -1)).sum() >= 1


def test_no_lookahead_past_values_unchanged_by_future_rows():
    rng = np.random.default_rng(7)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400)))
    full = supertrend(_frame(prices), 10, 3.0)
    for cut in (50, 150, 300):
        partial = supertrend(_frame(prices[:cut]), 10, 3.0)
        pd.testing.assert_frame_equal(partial, full.iloc[:cut])
