"""Tests for the Strategy A live runner (hold SPY + ORB overlay)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_orb_overlay import DayEngine, Settings, plan_entry, plan_exit, replay_day  # noqa: E402
from orb_backtest import ORBConfig, add_atr, simulate_day  # noqa: E402
from test_orb_backtest import OR_CLOSES, OR_HIGHS, OR_LOWS, make_atr_day, make_day  # noqa: E402

S = Settings(max_or_width_rel=None, skip_fomc=False)
CFG = ORBConfig(stop_mode="atr", atr_mult=3.0, take_profit_pct=None)


def _same(day, settings=S, cfg=CFG, adr=None):
    day = add_atr(day, 3)
    bt = simulate_day(day, cfg, adr)
    lv = replay_day(day, settings, adr)
    if bt is None:
        assert lv is None
        return None
    assert lv["direction"] == bt["direction"]
    assert lv["entry_price"] == pytest.approx(bt["entry_price"])
    assert lv["exit_price"] == pytest.approx(bt["exit_price"])
    assert lv["exit_reason"] == bt["exit_reason"]
    return lv


def test_engine_matches_backtest_long_trailing_stop():
    closes = [100.0] * 6 + [101.0, 102.0, 103.0, 104.0, 105.0, 104.6, 104.2, 100.0] + [100.0] * 58
    t = _same(make_atr_day("2026-01-05", closes, rng=1.0))
    assert t["exit_reason"] == "trail_stop"


def test_engine_matches_backtest_short_and_eod():
    closes = [100.0] * 6 + [99.0] + [98.8] * 65
    t = _same(make_atr_day("2026-01-05", closes, rng=1.0))
    assert t["direction"] == "short" and t["exit_reason"] == "eod"


def test_engine_matches_backtest_no_breakout():
    day = make_day(
        "2026-01-05", OR_CLOSES + [100.0] * 72, OR_HIGHS + [100.0] * 72, OR_LOWS + [100.0] * 72
    )
    assert _same(day) is None


def test_engine_width_filter_and_fomc_skip():
    day = make_day(
        "2026-01-05",
        OR_CLOSES + [101.5] + [102] * 71,
        OR_HIGHS + [101.5] + [102] * 71,
        OR_LOWS + [101.5] + [102] * 71,
    )
    s = Settings(max_or_width_rel=0.5, skip_fomc=False)
    cfg = ORBConfig(stop_mode="atr", atr_mult=3.0, take_profit_pct=None, max_or_width_rel=0.5)
    assert _same(day, s, cfg, adr=5.0) is not None
    assert _same(day, s, cfg, adr=3.0) is None
    fomc_day = make_day("2025-03-19", OR_CLOSES + [101.5] + [102] * 71)
    assert (
        replay_day(add_atr(fomc_day, 3), Settings(max_or_width_rel=None, skip_fomc=True), None)
        is None
    )


def test_live_price_tick_triggers_stop_and_eod():
    eng = DayEngine(day="2026-01-05")
    eng.phase, eng.direction, eng.entry_price, eng.stop = "in_trade", 1, 100.0, 98.0
    s = Settings()
    assert eng.on_price(98.5, pd.Timestamp("2026-01-05 11:00", tz="America/New_York"), s) is None
    act = eng.on_price(97.9, pd.Timestamp("2026-01-05 11:01", tz="America/New_York"), s)
    assert act == {"action": "exit", "reason": "stop", "ref_price": 97.9}
    eng2 = DayEngine(
        day="2026-01-05", phase="in_trade", direction=-1, entry_price=100.0, stop=103.0
    )
    act = eng2.on_price(99.0, pd.Timestamp("2026-01-05 15:57", tz="America/New_York"), s)
    assert act["reason"] == "eod"


def test_engine_state_roundtrip():
    eng = DayEngine(day="2026-01-05", phase="watch", or_high=101.0, or_low=99.0)
    assert DayEngine.from_dict(eng.to_dict()) == eng


def test_order_plan_long_doubles_and_short_sells_core():
    s = Settings(core_dollars=1000, overlay_dollars=1000)
    assert plan_entry(1, price=500.0, core_qty=2.0, s=s) == {"side": "buy", "notional": 1000.0}
    # Short overlay never goes net short: sell core shares worth $1000 (capped at what is held).
    assert plan_entry(-1, price=500.0, core_qty=2.5, s=s) == {"side": "sell", "qty": 2.0}
    assert plan_entry(-1, price=500.0, core_qty=1.5, s=s) == {"side": "sell", "qty": 1.5}
    assert plan_exit(1, overlay_qty=1.98) == {"side": "sell", "qty": 1.98}
    assert plan_exit(-1, overlay_qty=2.0) == {"side": "buy", "qty": 2.0}


# ------------------------------------------------------- full loop, fake broker


class FakeAlpaca:
    """Replays one session; the fake clock advances when the runner sleeps."""

    dry = False

    def __init__(self, day_bars, hist, clock):
        self.day, self.hist, self.clock_ref = day_bars, hist, clock
        self.orders, self.pos = [], 0.0

    def clock(self):
        d = self.day.index[0].normalize()
        return {
            "is_open": True,
            "next_open": str(d + pd.Timedelta(days=1, hours=9, minutes=30)),
            "next_close": str(d + pd.Timedelta(hours=16)),
        }

    def account(self):
        return {"buying_power": "1000000"}

    def position_qty(self, symbol):
        return self.pos

    def latest_price(self, symbol):
        done = self.day[self.day.index + pd.Timedelta(minutes=5) <= self.clock_ref[0]]
        return float((done if len(done) else self.day.iloc[:1])["close"].iloc[-1])

    def bars(self, symbol, start, end, feed):
        if feed == "sip":
            return self.hist
        return self.day[self.day.index <= self.clock_ref[0]]

    def order(self, symbol, side, qty=None, notional=None, ref_price=None):
        q = qty if qty is not None else notional / ref_price
        self.pos += q if side == "buy" else -q
        self.orders.append((self.clock_ref[0].strftime("%H:%M"), side, round(q, 6), ref_price))
        return q, ref_price


def test_full_day_loop_places_core_entry_and_exit(tmp_path, monkeypatch):
    import live_orb_overlay as lo

    hist = pd.concat(
        [
            make_atr_day(f"2026-01-{d:02d}", [100.0] * 78, rng=4.0)
            for d in range(1, 15)
            if d not in (3, 4, 10, 11)
        ]
    )
    closes = [100.0] * 6 + [101.0, 102.0, 103.0, 104.0, 105.0] + [105.0] * 67
    day = make_atr_day("2026-01-15", closes, rng=1.0)
    clock = [pd.Timestamp("2026-01-15 09:30", tz="America/New_York")]
    monkeypatch.setattr(lo, "_now", lambda: clock[0])

    def fake_sleep(sec):
        clock[0] += pd.Timedelta(minutes=1)

    monkeypatch.setattr(lo, "_sleep", fake_sleep)
    api = FakeAlpaca(day, hist, clock)
    s = Settings(skip_fomc=False, max_or_width_rel=0.4)
    assert lo.run(s, api, tmp_path) == 0
    sides = [o[1] for o in api.orders]
    assert sides == ["buy", "buy", "sell"]  # core, long overlay, overlay exit
    assert api.orders[1][0] == "10:05"  # first bar closing above range completes at 10:05
    assert api.orders[2][0] == "15:57"  # end-of-day exit
    assert api.pos == pytest.approx(api.orders[0][2])  # only the core remains
    state = (tmp_path / "spy_2026-01-15.json").read_text()
    assert '"exit_reason": "eod"' in state
