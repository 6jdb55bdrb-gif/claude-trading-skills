import json

import pandas as pd
from rsys import ohlcv

H4 = 4 * 3_600_000


class FakeExchange:
    """Serves synthetic 4h candles in pages of `page` rows, like ccxt.fetch_ohlcv."""

    def __init__(self, start, count, page=100, skip=()):
        self.rows = [
            [start + i * H4, 100 + i, 101 + i, 99 + i, 100.5 + i, 10.0]
            for i in range(count)
            if i not in skip
        ]
        self.page = page
        self.calls = 0

    def parse_timeframe(self, tf):
        return {"4h": 14_400, "1d": 86_400}[tf]

    def fetch_ohlcv(self, pair, timeframe, since=None, limit=None):
        self.calls += 1
        rows = [r for r in self.rows if r[0] >= since]
        return rows[: min(limit or self.page, self.page)]

    def milliseconds(self):
        return self.rows[-1][0] + H4 // 2  # last candle still open


def test_download_paginates_dedupes_and_drops_open_candle():
    ex = FakeExchange(start=0, count=350, page=100)
    df = ohlcv.download(ex, "BTC/USDT", "4h", start_ms=0, end_ms=None)
    assert len(df) == 349  # last candle is not closed yet
    assert df["timestamp"].is_monotonic_increasing
    assert df["timestamp"].duplicated().sum() == 0
    assert ex.calls >= 4


def test_download_respects_end():
    ex = FakeExchange(start=0, count=350)
    df = ohlcv.download(ex, "BTC/USDT", "4h", start_ms=0, end_ms=10 * H4)
    assert df["timestamp"].max() < 10 * H4


def test_validate_reports_gaps_and_bad_prices():
    ex = FakeExchange(start=0, count=50, skip={10, 11, 30})
    df = ohlcv.download(ex, "BTC/USDT", "4h", start_ms=0, end_ms=None)
    df.loc[5, "low"] = -1
    report = ohlcv.validate(df, "4h")
    assert report["missing_candles"] == 3
    assert report["gaps"] == 2
    assert report["bad_price_rows"] == 1
    assert report["ok"] is False


def test_csv_roundtrip_and_freqtrade_export(tmp_path):
    ex = FakeExchange(start=0, count=20)
    df = ohlcv.download(ex, "ETH/USDT", "4h", start_ms=0, end_ms=None)
    csv_path = ohlcv.save_csv(df, tmp_path / "canonical", "okx", "ETH/USDT", "4h")
    assert csv_path.name == "ETH_USDT-4h.csv"
    loaded = ohlcv.load_csv(csv_path)
    pd.testing.assert_frame_equal(loaded, df)

    ft_path = ohlcv.export_freqtrade(loaded, tmp_path / "ft", "ETH/USDT", "4h")
    assert ft_path.name == "ETH_USDT-4h.json"
    rows = json.loads(ft_path.read_text())
    assert rows[0] == [0, 100.0, 101.0, 99.0, 100.5, 10.0]
    assert len(rows) == len(df)
