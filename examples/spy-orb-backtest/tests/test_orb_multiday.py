"""Tests for the multi-day ORB engine with alternative exits."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orb_backtest import ORBConfig, add_atr, backtest  # noqa: E402
from orb_multiday import ExitRule, backtest_multiday  # noqa: E402
from test_orb_backtest import make_atr_day, make_day  # noqa: E402

FLAT_OR = [100.0] * 6  # opening range 99.5-100.5 with make_atr_day(rng=1)


def _days(*closes_lists, start=5, rng=1.0):
    return pd.concat(
        [make_atr_day(f"2026-01-{start + i:02d}", c, rng=rng) for i, c in enumerate(closes_lists)]
    )


def test_eod_rule_matches_existing_backtester():
    df = _days(
        FLAT_OR + [101.0, 102.0, 103.0, 104.0, 105.0, 104.6, 104.2, 100.0] + [100.0] * 58,
        FLAT_OR + [99.0] + [98.8] * 65,
        FLAT_OR + [100.0] * 72,
    )
    cfg = ORBConfig(stop_mode="atr", atr_mult=3, take_profit_pct=None, atr_period=3)
    old = backtest(df, cfg)
    new = backtest_multiday(add_atr(df, 3), cfg, ExitRule(kind="eod"))
    assert list(new["direction"]) == list(old["direction"])
    assert list(new["exit_price"]) == pytest.approx(list(old["exit_price"]))
    assert list(new["pnl"]) == pytest.approx(list(old["pnl"]))


def test_trade_carries_overnight_and_gap_through_stop_fills_at_open():
    day1 = FLAT_OR + [101.0] + [101.0] * 65  # long at 101, no stop hit
    day2 = make_day("2026-01-06", [90.0] * 72, opens=[90.0] * 72)  # gaps far below stop
    df = pd.concat([make_atr_day("2026-01-05", day1), day2])
    cfg = ORBConfig(stop_mode="atr", atr_mult=3, take_profit_pct=None, atr_period=3)
    t = backtest_multiday(add_atr(df, 3), cfg, ExitRule(kind="trail"))
    assert len(t) == 1
    assert t["entry_date"].iloc[0] == "2026-01-05" and t["exit_date"].iloc[0] == "2026-01-06"
    assert t["exit_price"].iloc[0] == pytest.approx(90.0)  # open, worse than the stop
    assert t["days_held"].iloc[0] == 1


def test_r_multiple_target_hit_on_day_two():
    day1 = FLAT_OR + [101.0] + [101.0] * 65  # entry 101, range stop 99.5 -> R = 1.5
    day2 = [101.0] * 10 + [102.0, 103.0, 104.0, 104.5] + [104.5] * 58  # 2R target = 104.0
    df = _days(day1, day2)
    cfg = ORBConfig(stop_mode="range", take_profit_pct=None, atr_period=3)
    t = backtest_multiday(add_atr(df, 3), cfg, ExitRule(kind="r_target", r_multiple=2.0))
    assert t["exit_reason"].iloc[0] == "target"
    assert t["exit_price"].iloc[0] == pytest.approx(104.0)
    assert t["exit_date"].iloc[0] == "2026-01-06"


def test_max_days_exits_at_close_of_last_day():
    day = FLAT_OR + [101.0] + [101.0] * 65
    later = [101.0] * 72
    df = _days(day, later, later, later)
    cfg = ORBConfig(stop_mode="atr", atr_mult=3, take_profit_pct=None, atr_period=3)
    t = backtest_multiday(add_atr(df, 3), cfg, ExitRule(kind="trail", max_days=2))
    assert t["exit_reason"].iloc[0] == "time"
    assert t["exit_date"].iloc[0] == "2026-01-07" and t["days_held"].iloc[0] == 2


def test_opposite_breakout_reverses_position():
    day1 = FLAT_OR + [101.0] + [101.0] * 65  # long
    day2 = [101.0] * 6 + [99.0] + [98.0] * 65  # day-2 range ~100.5-101.5; close 99 breaks down
    df = _days(day1, day2)
    cfg = ORBConfig(stop_mode="pct", stop_pct=5.0, take_profit_pct=None, atr_period=3)
    t = backtest_multiday(add_atr(df, 3), cfg, ExitRule(kind="reverse"))
    assert list(t["direction"]) == ["long", "short"]
    assert t["exit_reason"].iloc[0] == "opposite_breakout"
    assert t["entry_date"].iloc[1] == "2026-01-06"
    assert t["exit_reason"].iloc[1] == "end_of_data"


def test_only_one_position_at_a_time():
    day1 = FLAT_OR + [101.0] + [101.0] * 65
    day2 = [101.0] * 6 + [103.0] + [103.0] * 65  # another breakout up while still long
    df = _days(day1, day2)
    cfg = ORBConfig(stop_mode="pct", take_profit_pct=None, atr_period=3)
    t = backtest_multiday(add_atr(df, 3), cfg, ExitRule(kind="trail"))
    assert len(t) == 1
