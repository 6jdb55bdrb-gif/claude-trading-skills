import pandas as pd
import pytest
from silver_bullet import SilverBulletParams, prepare_bars, resample_bars, run_backtest, summarize

FLAT = (101.5, 101.7, 101.3, 101.5)


def params(**kw):
    base = dict(windows=("am",), max_risk_atr=10.0, cost_bps=0.0)
    base.update(kw)
    return SilverBulletParams(**base)


def test_bullish_setup_hits_liquidity_target(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)  # retrace fills at 100.5
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)  # runs to 106 buy-side liquidity
    trades, _ = run_backtest(bars_factory(overrides=path, after=FLAT), params())
    assert len(trades) == 1
    t = trades[0]
    assert t.direction == "long"
    assert t.entry == pytest.approx(100.5)
    assert t.target == pytest.approx(106.0)
    assert t.exit_reason == "target"
    assert t.stop < 98.5  # beyond the sweep extreme
    assert t.r_net == pytest.approx((106.0 - 100.5) / t.risk, rel=1e-3)
    assert t.entry_time.startswith("2026-03-04T10:05")


def test_ce_entry_uses_fvg_midpoint(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (100.5, 100.6, 99.8, 100.0)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    trades, _ = run_backtest(bars_factory(overrides=path, after=FLAT), params(entry_mode="ce"))
    assert trades[0].entry == pytest.approx((99.2 + 100.5) / 2)


def test_bullish_setup_stopped_out_is_minus_one_r(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:06"] = (100.5, 100.6, 97.0, 97.5)
    trades, _ = run_backtest(bars_factory(overrides=path, after=(97.5, 97.6, 97.4, 97.5)), params())
    assert trades[0].exit_reason == "stop"
    assert trades[0].r_gross == pytest.approx(-1.0)


def test_costs_reduce_r(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:06"] = (100.5, 100.6, 97.0, 97.5)
    df = bars_factory(overrides=path, after=(97.5, 97.6, 97.4, 97.5))
    t = run_backtest(df, params(cost_bps=5.0))[0][0]
    assert t.r_net < t.r_gross


def test_same_bar_stop_and_target_counts_as_loss(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:06"] = (100.9, 107.0, 97.0, 101.0)
    trades, _ = run_backtest(bars_factory(overrides=path, after=FLAT), params())
    assert trades[0].exit_reason == "stop"


def test_fill_bar_never_credits_target(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 107.0, 100.4, 106.5)  # fills AND trades through target
    path["10:06"] = (106.5, 106.6, 106.4, 106.5)
    trades, _ = run_backtest(bars_factory(overrides=path, after=FLAT), params())
    # target is checked from the next bar on: next bar opens above target -> exit at open
    assert trades[0].exit_reason == "target"
    assert trades[0].entry_time.startswith("2026-03-04T10:05")
    assert trades[0].exit_time.startswith("2026-03-04T10:06")


def test_no_sweep_no_trade_when_sweep_required(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:00"] = (99.9, 99.95, 99.85, 99.9)  # stays inside the reference range
    path["10:01"] = (99.9, 101.6, 99.85, 101.5)
    path["10:02"] = (101.5, 102.0, 100.5, 101.8)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    df = bars_factory(overrides=path, after=FLAT)
    assert run_backtest(df, params())[0] == []
    assert len(run_backtest(df, params(require_sweep=False, require_mss=False, min_rr=1.0))[0]) == 1


def test_unfilled_inside_window_is_not_traded(bars_factory, bull_core):
    path = dict(bull_core)
    path["11:05"] = (101.0, 101.1, 100.4, 100.9)  # retrace only after the window
    path["11:20"] = (101.0, 106.5, 100.9, 106.2)
    trades, diags = run_backtest(bars_factory(overrides=path, after=FLAT), params())
    assert trades == []
    assert any(d["status"] == "setup_unfilled" for d in diags)


def test_target_reached_before_fill_cancels_order(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:04"] = (101.8, 106.5, 101.6, 106.2)  # leaves without a retrace
    path["10:10"] = (101.0, 101.1, 100.4, 100.9)  # later touch of entry must not fill
    trades, _ = run_backtest(bars_factory(overrides=path, after=FLAT), params())
    assert trades == []


def test_min_rr_filter_rejects_close_liquidity(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    df = bars_factory(overrides=path, after=FLAT)
    df.loc[df.index[30], "high"] = 101.0  # remove the 106 liquidity pool
    assert run_backtest(df, params())[0] == []
    # fixed-R target still trades
    assert len(run_backtest(df, params(target_mode="rr"))[0]) == 1


def test_bearish_mirror_produces_short(bars_factory, bull_core, mirror_fn):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    df = mirror_fn(bars_factory(overrides=path, after=FLAT))
    trades, _ = run_backtest(df, params())
    assert len(trades) == 1
    t = trades[0]
    assert t.direction == "short"
    assert t.entry == pytest.approx(200 - 100.5)
    assert t.target == pytest.approx(200 - 106.0)
    assert t.exit_reason == "target"
    assert t.r_gross > 0


def test_weekend_skipped_unless_enabled(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    df = bars_factory(day="2026-03-07", overrides=path, after=FLAT)  # Saturday
    assert run_backtest(df, params())[0] == []
    assert len(run_backtest(df, params(include_weekends=True))[0]) == 1


def test_time_exit_at_flat_deadline(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    trades, _ = run_backtest(
        bars_factory(overrides=path, after=FLAT), params(flat_minutes_after_window=30)
    )
    t = trades[0]
    assert t.exit_reason == "time"
    assert t.exit_time.startswith("2026-03-04T11:29")
    assert t.exit == pytest.approx(101.5)


def test_setup_unaffected_by_future_bars(bars_factory, bull_core):
    """No look-ahead: truncating data after the fill bar keeps the same entry."""
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    full = bars_factory(overrides=path, after=FLAT)
    cut = full[full.index <= pd.Timestamp("2026-03-04 10:06", tz="America/New_York")]
    a = run_backtest(full, params())[0][0]
    b = run_backtest(cut, params())[0][0]
    assert (a.entry, a.stop, a.target, a.entry_time) == (b.entry, b.stop, b.target, b.entry_time)


def test_params_validation():
    with pytest.raises(ValueError):
        SilverBulletParams(windows=("asia",)).validate()
    with pytest.raises(ValueError):
        SilverBulletParams(entry_mode="market").validate()


def test_prepare_bars_rejects_missing_columns():
    df = pd.DataFrame({"open": [1.0]}, index=pd.DatetimeIndex(["2026-01-01"], tz="UTC"))
    with pytest.raises(ValueError):
        prepare_bars(df)


def test_resample_to_5m(bars_factory):
    bars = prepare_bars(bars_factory())
    r5 = resample_bars(bars, "5min")
    first = r5.iloc[6]  # 08:30 bucket
    assert first["high"] == pytest.approx(106.0)
    assert len(r5) == len(bars) // 5 + (1 if len(bars) % 5 else 0)


def test_summarize_basic_stats():
    from silver_bullet import Trade

    def mk(r, reason):
        return Trade("d", "am", "long", "", "", "", 1, 0, 2, 1, reason, 1, r, r, 0.1)

    s = summarize([mk(2.0, "target"), mk(-1.0, "stop"), mk(-1.0, "stop"), mk(2.0, "target")])
    assert s["trades"] == 4
    assert s["win_rate"] == 0.5
    assert s["expectancy_r"] == pytest.approx(0.5)
    assert s["profit_factor"] == pytest.approx(2.0)
    assert s["max_drawdown_r"] == pytest.approx(-2.0)
    assert summarize([]) == {"trades": 0}


def test_sweep_in_lead_zone_before_window_counts(bars_factory, bull_core):
    path = dict(bull_core)
    path["09:45"] = (99.9, 99.95, 98.0, 99.5)  # 09:30 open runs the pre-market low
    path["10:00"] = (99.5, 99.2, 98.9, 99.0)  # no new low inside the window
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    df = bars_factory(overrides=path, after=FLAT)
    trades, _ = run_backtest(df, params(require_mss=False))
    assert len(trades) == 1
    assert trades[0].stop < 98.0  # stop sits beyond the pre-window sweep extreme
    assert run_backtest(df, params(require_mss=False, sweep_lead_minutes=0))[0] == []


def test_cost_filter_rejects_tight_stops(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    df = bars_factory(overrides=path, after=FLAT)
    # risk ~2.1 on a ~100 price: 30 bp/side = 0.6 round trip = ~0.29R > 0.10R cap
    assert run_backtest(df, params(cost_bps=30.0))[0] == []
    assert len(run_backtest(df, params(cost_bps=30.0, max_cost_r=0.5))[0]) == 1


def test_bias_filter_blocks_countertrend_longs(bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    hist_days = pd.bdate_range("2026-01-26", "2026-03-03")
    flat_day = (100.0, 100.2, 99.8, 100.0)

    def history(level_fn):
        frames = []
        for k, d in enumerate(hist_days):
            lvl = level_fn(k)
            bar = tuple(x - 100.0 + lvl for x in flat_day)
            frames.append(bars_factory(day=str(d.date()), overrides={"08:30": bar}, after=bar))
        return frames

    today = bars_factory(overrides=path, after=FLAT)
    down = pd.concat(history(lambda k: 140.0 - k) + [today])  # falling -> bearish bias
    up = pd.concat(history(lambda k: 60.0 + k) + [today])
    assert run_backtest(down, params(bias_filter="sma", bias_sma_days=5))[0] == []
    assert len(run_backtest(up, params(bias_filter="sma", bias_sma_days=5))[0]) >= 1
