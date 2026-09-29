import numpy as np
import pandas as pd
import pytest
from rsys import finrl_agent, ohlcv

DAY = 86_400_000


def _write(tmp_path, pair, start_price, days=500, offset_days=0):
    ts = pd.Timestamp("2022-10-01", tz="UTC").value // 1_000_000 + offset_days * DAY
    rng = np.random.default_rng(len(pair))
    close = start_price * np.exp(np.cumsum(rng.normal(0, 0.02, days)))
    df = pd.DataFrame(
        {
            "timestamp": ts + np.arange(days) * DAY,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1.0,
        }
    )
    ohlcv.save_csv(df, tmp_path, "okx", pair, "1d")


def test_build_frame_aligns_dates_and_has_no_nan(tmp_path):
    _write(tmp_path, "BTC/USDT", 20_000)
    _write(tmp_path, "ETH/USDT", 1_300, offset_days=10)
    data = finrl_agent.build_frame(["BTC/USDT", "ETH/USDT"], "okx", tmp_path)
    assert set(data["tic"]) == {"BTC/USDT", "ETH/USDT"}
    assert data.groupby("date")["tic"].count().eq(2).all()
    assert not data[finrl_agent.TECH].isna().any().any()


def test_indicators_are_causal(tmp_path):
    _write(tmp_path, "BTC/USDT", 20_000)
    full = ohlcv.load_csv(tmp_path / "okx" / "BTC_USDT-1d.csv")
    a = finrl_agent.add_indicators(full)
    b = finrl_agent.add_indicators(full.iloc[:200])
    pd.testing.assert_frame_equal(a.iloc[:200][finrl_agent.TECH], b[finrl_agent.TECH])


def test_rescale_keeps_returns(tmp_path):
    _write(tmp_path, "BTC/USDT", 20_000)
    data = finrl_agent.build_frame(["BTC/USDT"], "okx", tmp_path)
    scaled, scales = finrl_agent.rescale_prices(data, "2022-12-01")
    first = scaled.loc[scaled["date"] >= "2022-12-01", "close"].iloc[0]
    assert first == pytest.approx(100.0)
    assert np.allclose(scaled["close"].pct_change().dropna(), data["close"].pct_change().dropna())


def test_splits_do_not_overlap():
    names = list(finrl_agent.SPLITS)
    for a, b in zip(names, names[1:]):
        assert finrl_agent.SPLITS[a][1] <= finrl_agent.SPLITS[b][0]


def test_summarize_basic():
    s = finrl_agent.summarize(pd.Series([100, 110, 99, 120]))
    assert s["total_return_pct"] == 20.0
    assert s["max_drawdown_pct"] == -10.0
