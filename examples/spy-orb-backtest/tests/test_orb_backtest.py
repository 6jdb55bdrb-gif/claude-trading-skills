"""Tests for the SPY 30-minute Opening Range Breakout backtester."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orb_backtest import (  # noqa: E402
    ORBConfig,
    add_atr,
    backtest,
    compute_metrics,
    opening_range,
    simulate_day,
)


def make_day(date: str, closes, highs=None, lows=None, opens=None) -> pd.DataFrame:
    """Build a regular-session day of 5-min bars starting 09:30 ET."""
    n = len(closes)
    idx = pd.date_range(f"{date} 09:30", periods=n, freq="5min", tz="America/New_York")
    opens = opens if opens is not None else [closes[0]] + list(closes[:-1])
    highs = highs if highs is not None else [max(o, c) for o, c in zip(opens, closes)]
    lows = lows if lows is not None else [min(o, c) for o, c in zip(opens, closes)]
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1000},
        index=idx,
    )


# 6 opening-range bars (09:30-09:55) fluctuating between 99 and 101.
OR_CLOSES = [100, 100.5, 99.5, 100, 100.2, 99.8]
OR_HIGHS = [101, 100.8, 100.1, 100.4, 100.6, 100.3]
OR_LOWS = [99.5, 99.9, 99, 99.6, 99.9, 99.4]


def test_opening_range_uses_first_30_minutes():
    day = make_day(
        "2026-01-05", OR_CLOSES + [100] * 72, OR_HIGHS + [100] * 72, OR_LOWS + [100] * 72
    )
    hi, lo, after = opening_range(day, minutes=30)
    assert hi == 101
    assert lo == 99
    assert after.index[0].strftime("%H:%M") == "10:00"


def test_long_breakout_held_to_close():
    rest = [100.5, 101.5, 102, 102.5] + [103] * 68  # breakout on 2nd post-OR bar
    day = make_day(
        "2026-01-05",
        OR_CLOSES + rest,
        OR_HIGHS + [max(c, 100.5) for c in rest],
        OR_LOWS + [min(c, 100.5) for c in rest],
    )
    trade = simulate_day(day, ORBConfig())
    assert trade is not None
    assert trade["direction"] == "long"
    assert trade["entry_price"] == pytest.approx(101.5)
    assert trade["exit_reason"] == "eod"
    assert trade["exit_price"] == pytest.approx(103)
    shares = 1000 / 101.5
    assert trade["pnl"] == pytest.approx(shares * (103 - 101.5))


def test_short_breakout_hits_5pct_stop():
    rest = [98.5] + [99] * 3 + [104] + [100] * 67
    highs = OR_HIGHS + [99, 99, 99, 99, 104] + [100] * 67
    lows = OR_LOWS + [98.4, 99, 99, 99, 99] + [100] * 67
    day = make_day("2026-01-05", OR_CLOSES + rest, highs, lows)
    trade = simulate_day(day, ORBConfig())
    assert trade["direction"] == "short"
    assert trade["entry_price"] == pytest.approx(98.5)
    stop = 98.5 * 1.05
    assert trade["exit_reason"] == "stop"
    assert trade["exit_price"] == pytest.approx(stop)
    # Loss is exactly 5% of the $1,000 position.
    assert trade["pnl"] == pytest.approx(-50.0)


def test_wick_through_range_without_close_is_not_a_breakout():
    rest = [100] * 72
    highs = OR_HIGHS + [102] + [100] * 71  # wick above 101 but closes inside
    day = make_day("2026-01-05", OR_CLOSES + rest, highs, OR_LOWS + [100] * 72)
    assert simulate_day(day, ORBConfig()) is None


def test_next_open_entry_mode():
    rest = [101.5, 102] + [102] * 70
    opens = OR_CLOSES + [100.5, 101.8] + [102] * 70
    day = make_day("2026-01-05", OR_CLOSES + rest, opens=opens)
    trade = simulate_day(day, ORBConfig(entry_mode="next_open"))
    assert trade["entry_price"] == pytest.approx(101.8)


def test_take_profit():
    rest = [101.5, 102, 106.7] + [101] * 69
    day = make_day("2026-01-05", OR_CLOSES + rest)
    trade = simulate_day(day, ORBConfig(take_profit_pct=5.0))
    assert trade["exit_reason"] == "target"
    assert trade["exit_price"] == pytest.approx(101.5 * 1.05)


def test_range_stop_mode_uses_opposite_side():
    rest = [101.5, 100, 98.9] + [100] * 69
    opens = OR_CLOSES + [100.5, 101.5, 100] + [100] * 69
    highs = OR_HIGHS + [101.5, 101.5, 100] + [100] * 69
    lows = OR_LOWS + [100.5, 100, 98.9] + [100] * 69
    day = make_day("2026-01-05", OR_CLOSES + rest, highs, lows, opens)
    trade = simulate_day(day, ORBConfig(stop_mode="range"))
    assert trade["exit_reason"] == "stop"
    assert trade["exit_price"] == pytest.approx(99)


def test_backtest_one_trade_per_day_and_fixed_size():
    d1 = make_day("2026-01-05", OR_CLOSES + [101.5] + [102] * 71)
    d2 = make_day("2026-01-06", OR_CLOSES + [98.5] + [98] * 71)
    trades = backtest(pd.concat([d1, d2]), ORBConfig())
    assert len(trades) == 2
    assert (trades["position_value"] == 1000).all()
    m = compute_metrics(trades, ORBConfig())
    assert m["num_trades"] == 2
    assert m["win_rate_pct"] == pytest.approx(100.0)
    assert m["total_pnl"] == pytest.approx(trades["pnl"].sum(), abs=0.01)


def test_gap_through_stop_fills_at_open():
    rest = [101.5] + [101] * 3 + [90] + [90] * 67
    opens = OR_CLOSES + [100.5, 101.5, 101, 101, 92] + [90] * 67
    day = make_day("2026-01-05", OR_CLOSES + rest, opens=opens)
    trade = simulate_day(day, ORBConfig())
    assert trade["exit_reason"] == "stop"
    assert trade["exit_price"] == pytest.approx(92)  # worse than the 96.425 stop


# --------------------------------------------------------------- ATR trailing


def make_atr_day(date, closes, rng=1.0):
    """Bars with constant high-low = rng and open = prior close -> ATR == rng."""
    opens = [closes[0]] + list(closes[:-1])
    # Centre each bar on its body so true range == rng when the body is <= rng.
    highs = [(o + c) / 2 + rng / 2 for o, c in zip(opens, closes)]
    lows = [(o + c) / 2 - rng / 2 for o, c in zip(opens, closes)]
    return make_day(date, closes, highs, lows, opens)


def test_default_take_profit_is_10pct():
    assert ORBConfig().take_profit_pct == 10.0


def test_add_atr_constant_range():
    day = make_atr_day("2026-01-05", [100.0] * 30, rng=1.0)
    out = add_atr(day, period=14)
    assert out["atr"].iloc[-1] == pytest.approx(1.0)


def test_atr_initial_stop_and_trailing_long():
    # OR flat at 100 (range 99.5-100.5); breakout close 101; rally to 105; drop to 100.
    closes = [100.0] * 6 + [101.0, 102.0, 103.0, 104.0, 105.0, 104.6, 104.2, 100.0] + [100.0] * 58
    day = add_atr(make_atr_day("2026-01-05", closes, rng=1.0), period=3)
    trade = simulate_day(day, ORBConfig(stop_mode="atr", atr_mult=2.0, take_profit_pct=None))
    assert trade["direction"] == "long"
    assert trade["entry_price"] == pytest.approx(101.0)
    assert trade["initial_stop"] == pytest.approx(101.0 - 2.0)  # entry - 2*ATR
    # Highest high reached = 105.5 (bar centred 104.5..105 + 0.5) -> trail = 105.5 - 2 = 103.5
    assert trade["exit_reason"] == "trail_stop"
    assert trade["stop_price"] > trade["initial_stop"]
    assert trade["pnl"] > 0


def test_atr_trailing_short_moves_down():
    closes = [100.0] * 6 + [99.0, 98.0, 97.0, 96.0, 95.0, 95.4, 99.0] + [99.0] * 59
    day = add_atr(make_atr_day("2026-01-05", closes, rng=1.0), period=3)
    trade = simulate_day(day, ORBConfig(stop_mode="atr", atr_mult=2.0, take_profit_pct=None))
    assert trade["direction"] == "short"
    assert trade["initial_stop"] == pytest.approx(101.0)
    assert trade["stop_price"] < trade["initial_stop"]
    assert trade["exit_reason"] == "trail_stop"
    assert trade["pnl"] > 0


def test_atr_stop_never_looser_than_max_loss_pct():
    # Huge ATR (range 20) -> 2*ATR stop would be > 5% away; 5% cap applies.
    closes = [100.0] * 6 + [111.0] + [111.0] * 65
    day = add_atr(make_atr_day("2026-01-05", closes, rng=20.0), period=3)
    trade = simulate_day(
        day, ORBConfig(stop_mode="atr", atr_mult=2.0, stop_pct=5.0, range_minutes=30)
    )
    if trade is not None:
        assert trade["initial_stop"] >= trade["entry_price"] * 0.95 - 1e-9


def test_leverage_measured_against_account_size():
    d1 = make_day("2026-01-05", OR_CLOSES + [101.5] + [102] * 71)
    cfg = ORBConfig(position_size=3000.0, account_size=1000.0, take_profit_pct=None)
    trades = backtest(d1, cfg)
    m = compute_metrics(trades, cfg)
    assert trades["pnl"].iloc[0] == pytest.approx(3000 / 101.5 * 0.5)
    assert m["leverage"] == pytest.approx(3.0)
    assert m["final_equity"] == pytest.approx(1000 + trades["pnl"].sum(), abs=0.01)
    assert m["total_return_on_account_pct"] == pytest.approx(trades["pnl"].sum() / 10, abs=0.01)


# ------------------------------------------------------------- feature 1: exit time


def test_exit_time_closes_at_bar_open():
    # Breakout at 10:00 bar close (101.5); price keeps rising; 11:00 bar opens at 103.
    rest = [101.5] + [102.0] * 11 + [104.0] + [105.0] * 59
    opens = OR_CLOSES + [100.5] + [102.0] * 11 + [103.0] + [105.0] * 59
    day = make_day("2026-01-05", OR_CLOSES + rest, opens=opens)
    trade = simulate_day(day, ORBConfig(exit_time="11:00", take_profit_pct=None))
    assert trade["exit_reason"] == "time"
    assert trade["exit_time"] == "11:00"
    assert trade["exit_price"] == pytest.approx(103.0)


def test_stop_before_exit_time_still_wins():
    rest = [98.5, 104.0] + [99.0] * 70
    highs = OR_HIGHS + [99.0, 104.0] + [99.0] * 70
    lows = OR_LOWS + [98.4, 98.5] + [99.0] * 70
    day = make_day("2026-01-05", OR_CLOSES + rest, highs, lows)
    trade = simulate_day(day, ORBConfig(exit_time="11:00"))
    assert trade["exit_reason"] == "stop"


def test_no_entry_at_or_after_exit_time():
    # First breakout only happens at 11:00 -> no trade when exit_time is 11:00.
    rest = [100.0] * 12 + [102.0] * 60
    day = make_day("2026-01-05", OR_CLOSES + rest, OR_HIGHS + rest, OR_LOWS + rest)
    assert simulate_day(day, ORBConfig(exit_time="11:00")) is None
    assert simulate_day(day, ORBConfig()) is not None


def test_max_hold_minutes_exits_n_minutes_after_entry():
    # Entry at close of 10:05 bar (=10:10); 60 min hold -> exit at open of 11:10 bar.
    rest = [100.0, 101.5] + [102.0] * 70
    opens = OR_CLOSES + [100.0, 100.0] + [102.0] * 12 + [103.0] + [102.0] * 57
    day = make_day("2026-01-05", OR_CLOSES + rest, opens=opens)
    trade = simulate_day(day, ORBConfig(max_hold_minutes=60, take_profit_pct=None))
    assert trade["entry_time"] == "10:05"
    assert trade["exit_reason"] == "time"
    assert trade["exit_time"] == "11:10"


# ------------------------------------------------------------- feature 2: skip dates


def test_skip_dates_removes_those_sessions():
    d1 = make_day("2026-01-05", OR_CLOSES + [101.5] + [102] * 71)
    d2 = make_day("2026-01-06", OR_CLOSES + [98.5] + [98] * 71)
    df = pd.concat([d1, d2])
    trades = backtest(df, ORBConfig(skip_dates=frozenset({"2026-01-06"})))
    assert list(trades["date"]) == ["2026-01-05"]


def test_fomc_calendar_and_loader(tmp_path):
    from orb_backtest import FOMC_DATES, load_skip_dates

    assert "2025-04-08" not in FOMC_DATES and "2025-03-19" in FOMC_DATES
    f = tmp_path / "skip.txt"
    f.write_text("# comment\n2026-01-06\n\n2026-02-03  # CPI\n")
    assert load_skip_dates(str(f)) == {"2026-01-06", "2026-02-03"}


# --------------------------------------------------------- feature 3: OR width filter


def test_or_width_filter_uses_prior_average_daily_range():
    day = make_day(
        "2026-01-05",
        OR_CLOSES + [101.5] + [102] * 71,
        OR_HIGHS + [101.5] + [102] * 71,
        OR_LOWS + [101.5] + [102] * 71,
    )
    # OR = 99..101 on a 100 open -> width 2.0%.
    cfg = ORBConfig(max_or_width_rel=0.5)
    assert simulate_day(day, cfg, adr_pct=5.0) is not None  # 2/5 = 0.4 <= 0.5
    assert simulate_day(day, cfg, adr_pct=3.0) is None  # 2/3 = 0.67 > 0.5
    assert simulate_day(day, cfg, adr_pct=None) is None  # no history -> sit out
    assert simulate_day(day, ORBConfig(), adr_pct=None) is not None  # filter off


def test_daily_range_average_excludes_current_day():
    from orb_backtest import prior_avg_daily_range

    days = []
    for k, rng in enumerate([1.0, 3.0, 5.0]):
        d = make_day(f"2026-01-0{5 + k}", [100.0] * 78, [100 + rng / 2] * 78, [100 - rng / 2] * 78)
        days.append(d)
    adr = prior_avg_daily_range(pd.concat(days), n=2)
    keys = sorted(adr)
    assert pd.isna(adr[keys[0]]) and pd.isna(adr[keys[1]])
    assert adr[keys[2]] == pytest.approx(2.0)  # mean of 1% and 3%, not today's 5%
