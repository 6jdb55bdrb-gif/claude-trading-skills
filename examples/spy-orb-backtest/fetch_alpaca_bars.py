#!/usr/bin/env python3
"""Download multi-year 5-minute bars from Alpaca's market data API to CSV.

The output CSV feeds straight into ``orb_backtest.py --csv``.

Auth: Alpaca's Trading API keys go in the ``APCA-API-KEY-ID`` and
``APCA-API-SECRET-KEY`` headers, read from ALPACA_API_KEY / ALPACA_SECRET_KEY.
The free Basic plan includes historical SIP bars more than 15 minutes old.

    python3 fetch_alpaca_bars.py --symbol SPY --years 4 --out data/spy_5m.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"


def build_url(symbol, start, end, timeframe="5Min", feed="sip", page_token=None, limit=10000):
    params = {
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "limit": limit,
        "adjustment": "split",
        "feed": feed,
        "sort": "asc",
    }
    if page_token:
        params["page_token"] = page_token
    return BASE.format(symbol=symbol) + "?" + urllib.parse.urlencode(params)


def get_json(url, headers, retries=5):
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2**attempt)
                continue
            body = e.read()[:300].decode(errors="replace")
            raise SystemExit(f"Alpaca HTTP {e.code}: {body}") from e
    raise SystemExit("Alpaca: too many retries")


def fetch_bars(symbol, start, end, headers, feed="sip", fetch=get_json):
    """Yield bar dicts across all pages."""
    token = None
    while True:
        data = fetch(build_url(symbol, start, end, feed=feed, page_token=token), headers)
        yield from data.get("bars") or []
        token = data.get("next_page_token")
        if not token:
            return


def write_csv(bars, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    n = 0
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for b in bars:
            w.writerow([b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]])
            n += 1
    return n


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--symbol", default="SPY")
    p.add_argument("--years", type=float, default=4)
    p.add_argument("--start", help="ISO date; overrides --years")
    p.add_argument("--end", help="ISO date (default: now - 20 min)")
    p.add_argument("--feed", default="sip", choices=["sip", "iex"])
    p.add_argument("--out", default="data/spy_5m.csv")
    a = p.parse_args(argv)

    key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        print(
            "Set ALPACA_API_KEY and ALPACA_SECRET_KEY (free key at https://alpaca.markets/)",
            file=sys.stderr,
        )
        return 1
    headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}

    now = datetime.now(timezone.utc)
    end = a.end or (now - timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    start = a.start or (now - timedelta(days=round(365.25 * a.years))).strftime("%Y-%m-%d")
    n = write_csv(fetch_bars(a.symbol, start, end, headers, a.feed), a.out)
    print(f"Wrote {n} bars for {a.symbol} {start} -> {end} to {a.out}")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
