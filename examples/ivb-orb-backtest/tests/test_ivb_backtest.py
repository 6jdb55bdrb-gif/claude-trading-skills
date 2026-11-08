import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ivb_backtest as ivb  # noqa: E402


def make_day(date, bars, minutes=60, vol=None):
    """bars: list of (o,h,l,c). Starts 09:30 ET."""
    start = pd.Timestamp(f"{date} 09:30", tz=ivb.ET)
    idx = [start + pd.Timedelta(minutes=minutes * i) for i in range(len(bars))]
    df = pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = vol if vol is not None else [1000] * len(bars)
    return df


FLAT = [(100, 101, 99, 100)] * 7


def history(n=25):
    days = pd.bdate_range("2024-01-01", periods=n)
    return [make_day(d.date(), FLAT) for d in days]


def test_long_breakout_held_to_close():
    test = make_day(
        "2024-03-01",
        [
            (100, 101, 99, 100.5),
            (100.5, 102, 100.4, 101.8),
            (101.8, 103, 101.5, 102.9),
            (102.9, 104, 102.5, 103.5),
            (103.5, 104, 103, 103.8),
            (103.8, 104.5, 103.5, 104.2),
            (104.2, 105, 104, 105),
        ],
    )
    df = pd.concat(history() + [test])
    trades = ivb.run_backtest(df, ivb.Params(cost_bps=0))
    t = [x for x in trades if x.date == "2024-03-01"][0]
    assert t.side == 1 and t.entry == 101.8 and t.stop == 99 and t.exit_reason == "close"
    assert t.exit == 105
    assert t.r_multiple == pytest.approx((105 - 101.8) / (101.8 - 99), rel=1e-3)


def test_short_breakout_stopped_at_ib_high():
    test = make_day(
        "2024-03-01",
        [(100, 101, 99, 100), (100, 100.2, 98, 98.2), (98.2, 101.5, 98, 101.2)] + FLAT[:4],
    )
    df = pd.concat(history() + [test])
    t = [x for x in ivb.run_backtest(df, ivb.Params(cost_bps=0)) if x.date == "2024-03-01"][0]
    assert t.side == -1 and t.exit_reason == "stop" and t.exit == 101
    assert t.r_multiple == pytest.approx(-1.0, rel=1e-3)


def test_rvol_filter_blocks_weak_breakout_and_no_retry():
    # breakout on average volume, later bar breaks again on high volume -> still no trade (first break decides)
    vol = [1000, 1000, 5000, 1000, 1000, 1000, 1000]
    test = make_day(
        "2024-03-01",
        [(100, 101, 99, 100), (100, 101.5, 100, 101.4), (101.4, 103, 101, 102.9)] + FLAT[:4],
        vol=vol,
    )
    df = pd.concat(history() + [test])
    trades = ivb.run_backtest(df, ivb.Params(rvol_min=1.5, cost_bps=0))
    assert not [x for x in trades if x.date == "2024-03-01"]


def test_rvol_filter_passes_strong_breakout():
    vol = [1000, 3000, 1000, 1000, 1000, 1000, 1000]
    test = make_day(
        "2024-03-01", [(100, 101, 99, 100), (100, 101.5, 100, 101.45)] + FLAT[:5], vol=vol
    )
    df = pd.concat(history() + [test])
    t = [
        x
        for x in ivb.run_backtest(df, ivb.Params(rvol_min=1.5, clv_min=0.7, cost_bps=0))
        if x.date == "2024-03-01"
    ]
    assert t and t[0].rvol == pytest.approx(3.0)


def test_breakout_bar_stop_and_target():
    test = make_day(
        "2024-03-01",
        [(100, 101, 99, 100), (100.5, 102, 101, 102), (102, 105, 101.9, 104.5)] + FLAT[:4],
    )
    df = pd.concat(history() + [test])
    p = ivb.Params(stop_mode="breakout_bar", target_r=2, cost_bps=0)
    t = [x for x in ivb.run_backtest(df, p) if x.date == "2024-03-01"][0]
    assert t.stop == 101 and t.exit_reason == "target" and t.exit == 104
    assert t.r_multiple == pytest.approx(2.0)


def test_rvol_uses_only_past_days():
    df = pd.concat(history(25))
    df.iloc[-7:, df.columns.get_loc("volume")] = 10_000  # last day huge volume
    out = ivb.add_rvol(df, 20)
    assert out["rvol"].iloc[-1] == pytest.approx(10.0)  # avg excludes today


def test_metrics_basic():
    tr = [
        ivb.Trade("2024-01-02", 1, "10:30", 1, 0.9, "16:00", 1.2, "close", 2.0, 2.0, 1, 1),
        ivb.Trade("2024-01-03", 1, "10:30", 1, 0.9, "11:30", 0.9, "stop", -1.0, -1.0, 1, 1),
    ]
    m = ivb.metrics(tr)
    assert m["trades"] == 2 and m["win_rate"] == 0.5 and m["profit_factor"] == 2.0
