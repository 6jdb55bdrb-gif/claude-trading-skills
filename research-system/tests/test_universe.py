import json
from datetime import datetime, timezone

import pytest
from rsys import universe
from rsys.config import load_settings

DAY_MS = 86_400_000
START = "2022-10-01"
START_MS = int(datetime(2022, 10, 1, tzinfo=timezone.utc).timestamp() * 1000)


def _coin(rank, symbol, volume=1e9, tags=(), mcap=None):
    return {
        "id": rank,
        "name": symbol.title(),
        "symbol": symbol,
        "cmc_rank": rank,
        "tags": list(tags),
        "quote": {"USD": {"market_cap": mcap or 1e12 / rank, "volume_24h": volume}},
    }


@pytest.fixture
def settings():
    s = load_settings()
    s["universe"]["max_pairs"] = 5
    return s


@pytest.fixture
def listings():
    return [
        _coin(1, "BTC"),
        _coin(2, "ETH"),
        _coin(3, "USDT", tags=["stablecoin", "asset-backed-stablecoin"]),
        _coin(4, "XRP"),
        _coin(5, "USDC", tags=["stablecoin"]),
        _coin(6, "SOL"),
        _coin(7, "WBTC", tags=["wrapped-tokens"]),
        _coin(8, "LOWV", volume=10_000_000),
        _coin(9, "NEWC"),
        _coin(10, "NOPAIR"),
        _coin(11, "ADA"),
        _coin(12, "DOGE"),
        _coin(60, "FAR"),
    ]


def test_filter_listings_rejects_with_reasons(settings, listings):
    accepted, rejected = universe.filter_listings(listings, settings)
    symbols = [c["symbol"] for c in accepted]
    assert symbols[:2] == ["BTC", "ETH"]
    reasons = {r["symbol"]: r["reason"] for r in rejected}
    assert "stablecoin" in reasons["USDT"]
    assert "stablecoin" in reasons["USDC"]
    assert "wrapped" in reasons["WBTC"]
    assert "volume" in reasons["LOWV"]
    assert "rank" in reasons["FAR"]
    assert "FAR" not in symbols


def test_symbol_exclusion_list_applies_without_tags(settings):
    accepted, rejected = universe.filter_listings([_coin(1, "BTC"), _coin(2, "FDUSD")], settings)
    assert [c["symbol"] for c in accepted] == ["BTC"]
    assert "exclude list" in rejected[0]["reason"]


def test_build_universe_maps_pairs_checks_history_and_caps(settings, listings):
    markets = {
        f"{s}/USDT": {"spot": True, "active": True}
        for s in ["BTC", "ETH", "XRP", "SOL", "NEWC", "ADA", "DOGE"]
    }
    first_candle = {f"{s}/USDT": START_MS for s in ["BTC", "ETH", "XRP", "SOL", "ADA", "DOGE"]}
    first_candle["NEWC/USDT"] = START_MS + 200 * DAY_MS

    result = universe.build_universe(
        listings,
        settings,
        markets=markets,
        first_candle_ms=lambda pair: first_candle[pair],
        as_of="2026-09-29T00:00:00Z",
    )
    pairs = [a["pair"] for a in result["assets"]]
    assert pairs == ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT", "ADA/USDT"]
    reasons = {r["symbol"]: r["reason"] for r in result["rejected"]}
    assert "history" in reasons["NEWC"]
    assert "no active" in reasons["NOPAIR"]
    assert "max_pairs" in reasons["DOGE"]
    btc = result["assets"][0]
    assert btc["survivorship_biased"] is False
    assert result["assets"][2]["survivorship_biased"] is True
    assert result["source"] == "coinmarketcap:/v1/cryptocurrency/listings/latest"
    json.dumps(result)  # serialisable


def test_always_include_survives_even_if_filtered(settings):
    listings = [_coin(1, "BTC", volume=1), _coin(2, "ETH")]
    markets = {
        "BTC/USDT": {"spot": True, "active": True},
        "ETH/USDT": {"spot": True, "active": True},
    }
    result = universe.build_universe(
        listings, settings, markets=markets, first_candle_ms=lambda p: START_MS, as_of="x"
    )
    assert [a["pair"] for a in result["assets"]] == ["BTC/USDT", "ETH/USDT"]


def test_fetch_listings_requires_key(monkeypatch):
    monkeypatch.delenv("CMC_API_KEY", raising=False)
    with pytest.raises(universe.MissingApiKey):
        universe.fetch_listings(api_key=None)


def test_fetch_listings_sends_key_in_header_not_url(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"status": {"error_code": 0}, "data": [_coin(1, "BTC")]}).encode()

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        return FakeResp()

    monkeypatch.setattr(universe.urllib.request, "urlopen", fake_urlopen)
    data = universe.fetch_listings(api_key="secret-key", limit=100)
    assert data[0]["symbol"] == "BTC"
    assert "secret-key" not in captured["url"]
    assert captured["headers"]["X-cmc_pro_api_key"] == "secret-key"
    assert "limit=100" in captured["url"]
