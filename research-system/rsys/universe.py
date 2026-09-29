"""DATA ENGINEER: live asset universe from the CoinMarketCap API, mapped to exchange pairs.

Pipeline: CMC listings/latest (live) -> rank / volume / stablecoin / wrapped filters
-> spot pair exists on the data exchange -> >= start date of candle history -> cap.
Every rejected coin is kept with its reason so the REVIEWER can audit the universe.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone

CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
SOURCE = "coinmarketcap:/v1/cryptocurrency/listings/latest"
HISTORY_GRACE_DAYS = 7


class MissingApiKey(RuntimeError):
    pass


def fetch_listings(api_key: str | None, limit: int = 100, retries: int = 4) -> list[dict]:
    """Fetch live listings sorted by market cap. The key goes in a header, never the URL."""
    api_key = api_key or os.environ.get("CMC_API_KEY")
    if not api_key:
        raise MissingApiKey(
            "CMC_API_KEY is not set. Add it as an environment variable (never commit it)."
        )
    query = urllib.parse.urlencode(
        {"start": 1, "limit": limit, "convert": "USD", "sort": "market_cap"}
    )
    request = urllib.request.Request(
        f"{CMC_URL}?{query}",
        headers={"X-CMC_PRO_API_KEY": api_key, "Accept": "application/json"},
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                payload = json.loads(resp.read())
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"CoinMarketCap returned HTTP {exc.code}") from None
    status = payload.get("status", {})
    if status.get("error_code"):
        raise RuntimeError(f"CoinMarketCap error: {status.get('error_message')}")
    return payload["data"]


def _usd(coin: dict, field: str) -> float:
    return float((coin.get("quote", {}).get("USD", {}) or {}).get(field) or 0.0)


def filter_listings(listings: list[dict], settings: dict) -> tuple[list[dict], list[dict]]:
    cfg = settings["universe"]
    excluded = {s.upper() for s in cfg["exclude_symbols"]}
    keywords = [k.lower() for k in cfg["exclude_tag_keywords"]]
    always = {s.upper() for s in cfg["always_include"]}
    accepted, rejected = [], []
    for coin in sorted(listings, key=lambda c: c.get("cmc_rank") or 10**9):
        symbol = coin["symbol"].upper()
        tags = [str(t).lower() for t in coin.get("tags") or []]
        tag_hit = next((k for k in keywords for t in tags if k in t), None)
        reason = None
        if symbol in always:
            reason = None
        elif (coin.get("cmc_rank") or 10**9) > cfg["top_n"]:
            reason = f"rank {coin.get('cmc_rank')} outside top {cfg['top_n']}"
        elif symbol in excluded:
            reason = "on exclude list (stablecoin/wrapped/gold)"
        elif tag_hit:
            reason = f"CMC tag matches '{tag_hit}'"
        elif _usd(coin, "volume_24h") < cfg["min_volume_24h_usd"]:
            reason = (
                f"24h volume ${_usd(coin, 'volume_24h'):,.0f} < ${cfg['min_volume_24h_usd']:,.0f}"
            )
        if reason:
            rejected.append({"symbol": symbol, "cmc_rank": coin.get("cmc_rank"), "reason": reason})
        else:
            accepted.append(coin)
    return accepted, rejected


def _start_ms(settings: dict) -> int:
    start = datetime.strptime(settings["data"]["start"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(start.timestamp() * 1000)


def build_universe(
    listings: list[dict],
    settings: dict,
    markets: dict,
    first_candle_ms: Callable[[str], int | None],
    as_of: str | None = None,
) -> dict:
    cfg, quote = settings["universe"], settings["data"]["quote"]
    always = [s.upper() for s in cfg["always_include"]]
    accepted, rejected = filter_listings(listings, settings)
    deadline = _start_ms(settings) + HISTORY_GRACE_DAYS * 86_400_000
    assets = []
    for coin in accepted:
        symbol = coin["symbol"].upper()
        pair = f"{symbol}/{quote}"
        market = markets.get(pair)
        base = {"symbol": symbol, "cmc_rank": coin.get("cmc_rank")}
        if not market or not market.get("spot") or market.get("active") is False:
            rejected.append({**base, "reason": f"no active {pair} spot market on exchange"})
            continue
        if len(assets) >= cfg["max_pairs"] and symbol not in always:
            rejected.append({**base, "reason": f"over max_pairs={cfg['max_pairs']}"})
            continue
        first = first_candle_ms(pair)
        if first is None or first > deadline:
            rejected.append(
                {**base, "reason": f"insufficient history before {settings['data']['start']}"}
            )
            continue
        assets.append(
            {
                **base,
                "pair": pair,
                "name": coin.get("name"),
                "market_cap_usd": _usd(coin, "market_cap"),
                "volume_24h_usd": _usd(coin, "volume_24h"),
                "first_candle": datetime.fromtimestamp(first / 1000, tz=timezone.utc)
                .date()
                .isoformat(),
                # Only the always-included majors were top-ranked for the whole backtest window.
                "survivorship_biased": symbol not in always,
            }
        )
    return {
        "role": "DATA ENGINEER",
        "source": SOURCE,
        "as_of": as_of or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exchange": settings["data"]["exchange"],
        "filters": {
            k: cfg[k] for k in ("top_n", "min_volume_24h_usd", "max_pairs", "always_include")
        },
        "assets": assets,
        "rejected": rejected,
        "warning": (
            "Universe is today's CMC snapshot. Pairs with survivorship_biased=true were chosen "
            "with hindsight; treat their backtests as optimistic. BTC/ETH are primary evidence."
        ),
    }
