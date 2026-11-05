import json

import pytest
from backtest_silver_bullet import GRID, grid_params, main, parse_symbols, verdict
from data_sources import load_csv, parse_source
from silver_bullet import SilverBulletParams


def test_parse_symbols_and_sources():
    assert parse_symbols("BTC=binance:BTCUSDT, NQ=yahoo:NQ=F") == [
        ("BTC", "binance:BTCUSDT"),
        ("NQ", "yahoo:NQ=F"),
    ]
    with pytest.raises(ValueError):
        parse_symbols("BTCUSDT")
    with pytest.raises(ValueError):
        parse_source("ftp:foo")


def test_grid_size_and_variation():
    gp = grid_params(SilverBulletParams())
    expected = 1
    for v in GRID.values():
        expected *= len(v)
    assert len(gp) == expected == 96
    assert {g.entry_mode for g in gp} == {"edge", "ce"}


def _stats(exp, lo, n=50):
    return {"trades": n, "expectancy_r": exp, "expectancy_ci95": [lo, exp + 0.2]}


def test_verdict_rules():
    pos = {"trades": 20, "expectancy_r": 0.1}
    neg = {"trades": 20, "expectancy_r": -0.1}
    assert verdict(_stats(0.2, 0.05), (pos, pos), 0.8) == "ROBUST_EDGE"
    assert verdict(_stats(0.2, 0.05), (pos, pos), 0.3) == "POSITIVE_UNCONFIRMED"
    assert verdict(_stats(0.2, -0.05), (pos, pos), None) == "POSITIVE_UNCONFIRMED"
    assert verdict(_stats(0.2, -0.05), (pos, neg), None) == "UNSTABLE"
    assert verdict(_stats(-0.1, -0.3), (neg, neg), None) == "NO_EDGE"
    assert verdict(_stats(0.5, 0.1, n=5), (pos, pos), None) == "INSUFFICIENT_SAMPLE"


def test_end_to_end_csv(tmp_path, bars_factory, bull_core):
    path = dict(bull_core)
    path["10:05"] = (101.0, 101.1, 100.4, 100.9)
    path["10:20"] = (101.0, 106.5, 100.9, 106.2)
    df = bars_factory(overrides=path, after=(101.5, 101.7, 101.3, 101.5))
    csv = tmp_path / "bars.csv"
    df.to_csv(csv, index_label="timestamp")
    assert len(load_csv(csv)) == len(df)
    out = tmp_path / "out"
    rc = main(
        [
            "--symbols",
            f"T=csv:{csv}",
            "--timeframes",
            "1m",
            "--windows",
            "am",
            "--output-dir",
            str(out),
            "--grid",
        ]
    )
    assert rc == 0
    data = json.loads(next(out.glob("*.json")).read_text())
    res = data["results"][0]
    assert res["stats"]["trades"] == 1
    assert res["verdict"] == "INSUFFICIENT_SAMPLE"
    assert len(res["grid"]) == 96
    assert "ICT Silver Bullet Backtest" in next(out.glob("*.md")).read_text()


def test_bad_window_returns_error(tmp_path):
    assert (
        main(["--symbols", "T=csv:x.csv", "--windows", "asia", "--output-dir", str(tmp_path)]) == 1
    )


def test_yahoo_without_yfinance_exits_2(monkeypatch):
    import sys

    import data_sources

    monkeypatch.setattr(data_sources, "HAS_YFINANCE", False)
    monkeypatch.setitem(sys.modules, "yfinance", None)
    with pytest.raises(SystemExit) as exc:
        data_sources.fetch_yahoo("SPY", "5m", 5)
    assert exc.value.code == 2


def test_binance_fetch_paginates_with_fake_session():
    from datetime import datetime, timezone

    import data_sources

    class Resp:
        status_code = 200

        def __init__(self, rows):
            self._rows = rows

        def raise_for_status(self):
            pass

        def json(self):
            return self._rows

    class Sess:
        calls = 0

        def get(self, url, params, timeout):
            Sess.calls += 1
            start = params["startTime"]
            if start >= params["endTime"]:
                return Resp([])
            rows = [[start + k * 60_000, "1", "2", "0.5", "1.5", "10"] for k in range(1000)]
            rows = [r for r in rows if r[0] < params["endTime"]]
            return Resp(rows)

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    df = data_sources.fetch_binance("BTCUSDT", "1m", start, end, session=Sess())
    assert len(df) == 1440
    assert Sess.calls == 2
    assert list(df.columns) == ["open", "high", "low", "close"]
