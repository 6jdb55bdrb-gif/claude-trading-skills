"""Offline tests for the Alpaca bar downloader."""

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fetch_alpaca_bars import build_url, fetch_bars, write_csv  # noqa: E402
from orb_backtest import load_csv  # noqa: E402


def test_build_url_params():
    q = parse_qs(urlparse(build_url("SPY", "2022-01-01", "2022-02-01", page_token="abc")).query)
    assert q["timeframe"] == ["5Min"] and q["feed"] == ["sip"] and q["page_token"] == ["abc"]


def test_pagination_and_csv_roundtrip(tmp_path):
    pages = [
        {
            "bars": [{"t": "2022-01-03T14:30:00Z", "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10}],
            "next_page_token": "p2",
        },
        {
            "bars": [{"t": "2022-01-03T14:35:00Z", "o": 1.5, "h": 2, "l": 1, "c": 1.8, "v": 5}],
            "next_page_token": None,
        },
    ]
    calls = []

    def fake(url, headers):
        calls.append(url)
        return pages[len(calls) - 1]

    out = tmp_path / "bars.csv"
    assert write_csv(fetch_bars("SPY", "a", "b", {}, fetch=fake), str(out)) == 2
    assert "page_token=p2" in calls[1]
    df = load_csv(str(out))
    # UTC timestamps convert to 09:30 / 09:35 ET.
    assert [t.strftime("%H:%M") for t in df.index] == ["09:30", "09:35"]


def test_fetch_bars_passes_timeframe():
    calls = []

    def fake(url, headers):
        calls.append(url)
        return {"bars": [], "next_page_token": None}

    list(fetch_bars("SPY", "a", "b", {}, timeframe="1Min", fetch=fake))
    assert "timeframe=1Min" in calls[0]
