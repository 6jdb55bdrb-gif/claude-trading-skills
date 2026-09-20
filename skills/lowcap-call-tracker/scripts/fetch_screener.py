#!/usr/bin/env python3
"""Fetch screener rows for a lowcap variant and normalize them into hits.

Three data paths, in preference order:

1. ``elite``   — FINVIZ Elite CSV export (``export.ashx?...&auth=$FINVIZ_API_KEY``).
2. ``public``  — public screener HTML, parsed with BeautifulSoup (optional dep).
3. ``fixture`` — a local JSON file; used by tests, dry runs and offline replay.

Each FinViz view carries a different column set, so one variant issues several
requests (overview / ownership / performance / technical) that are merged on
ticker. ETF variants skip the ownership view: FinViz publishes no float or
short-float data for ETFs.

CLI:
    python3 fetch_screener.py --variant squeeze --fixture fixtures/dry_run_hits.json
    python3 fetch_screener.py --variant etf_momentum --mode public --json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import time
from typing import Any
from urllib.parse import quote

from screener_variants import (
    VIEW_CODES,
    build_variant_urls,
    elite_mode,
    get_variant,
    variant_filters,
    variant_views,
)

from config import load_config

try:
    import requests

    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - reported at call time
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup

    HAS_BS4 = True
except ImportError:  # pragma: no cover - public mode degrades with a message
    HAS_BS4 = False

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125"
ROWS_PER_PAGE = 20

# FinViz column header -> canonical hit field.
COLUMN_MAP: dict[str, str] = {
    "ticker": "ticker",
    "company": "company",
    "sector": "sector",
    "industry": "industry",
    "country": "country",
    "market cap": "market_cap",
    "price": "price",
    "change": "change_pct",
    "change %": "change_pct",
    "volume": "volume",
    "avg volume": "avg_volume",
    "average volume": "avg_volume",
    "rel volume": "rel_volume",
    "relative volume": "rel_volume",
    "float": "float_shares",
    "shs float": "float_shares",
    "outstanding": "shares_outstanding",
    "shs outstand": "shares_outstanding",
    "float short": "short_float_pct",
    "short float": "short_float_pct",
    "short float / ratio": "short_float_pct",
    "short ratio": "short_ratio",
    "inst own": "inst_own_pct",
    "insider trans": "insider_trans_pct",
    "sma20": "sma20_pct",
    "sma50": "sma50_pct",
    "sma200": "sma200_pct",
    "52w high": "high52w_pct",
    "52w low": "low52w_pct",
    "rsi": "rsi",
    "rsi (14)": "rsi",
    "atr": "atr",
    "atr (14)": "atr",
    "beta": "beta",
    "gap": "gap_pct",
    "gap %": "gap_pct",
    "from open": "from_open_pct",
    "change from open %": "from_open_pct",
    "volatility w": "volatility_week_pct",
    "volatility m": "volatility_month_pct",
    "perf week": "perf_week_pct",
    "perf month": "perf_month_pct",
    "perf quart": "perf_quarter_pct",
    "perf year": "perf_year_pct",
    "perf half": "perf_half_pct",
    "perf ytd": "perf_ytd_pct",
}

PERCENT_FIELDS = {
    "change_pct",
    "volatility_week_pct",
    "volatility_month_pct",
    "perf_half_pct",
    "perf_ytd_pct",
    "short_float_pct",
    "inst_own_pct",
    "insider_trans_pct",
    "sma20_pct",
    "sma50_pct",
    "sma200_pct",
    "high52w_pct",
    "low52w_pct",
    "gap_pct",
    "from_open_pct",
    "perf_week_pct",
    "perf_month_pct",
    "perf_quarter_pct",
    "perf_year_pct",
}
NUMERIC_FIELDS = {"price", "rel_volume", "rsi", "atr", "beta", "short_ratio"}
MAGNITUDE_FIELDS = {"market_cap", "float_shares", "shares_outstanding", "volume", "avg_volume"}

_MULTIPLIERS = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


class FetchError(RuntimeError):
    """Raised when screener data cannot be retrieved."""


def parse_number(raw: Any) -> float | None:
    """Parse a FinViz numeric cell ("12.34", "-", "1.2B", "5.10%", "1,234")."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "—", "N/A", "n/a", "null"}:
        return None
    multiplier = 1.0
    if text and text[-1].upper() in _MULTIPLIERS:
        multiplier = _MULTIPLIERS[text[-1].upper()]
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map one raw screener row (any view) onto canonical field names."""
    out: dict[str, Any] = {}
    for header, value in row.items():
        key = COLUMN_MAP.get(str(header).strip().lower())
        if not key or key in out:
            continue
        if key in PERCENT_FIELDS or key in NUMERIC_FIELDS or key in MAGNITUDE_FIELDS:
            out[key] = parse_number(value)
        else:
            text = str(value).strip()
            out[key] = text or None
    if out.get("ticker"):
        out["ticker"] = str(out["ticker"]).strip().upper()
    return out


def _export_url(config: dict[str, Any], filters: list[str], view: str, order: str | None) -> str:
    auth = os.environ.get("FINVIZ_API_KEY", "")
    encoded = quote(",".join(filters), safe=",_.-|")
    url = f"https://elite.finviz.com/export.ashx?v={VIEW_CODES[view]}&f={encoded}"
    if order:
        url += f"&o={order}"
    return f"{url}&auth={auth}"


def _http_get(url: str, timeout: int = 30) -> str:
    if not HAS_REQUESTS:
        raise FetchError("the 'requests' package is required for live screening")
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} from {url.split('&auth=')[0]}")
    return response.text


def parse_export_csv(text: str) -> list[dict[str, Any]]:
    rows = list(csv.DictReader(io.StringIO(text)))
    return [normalize_row(row) for row in rows if row]


# The results table carries this class; everything else on the page (filter
# dropdowns, view switcher, order-by menu) is chrome that also contains the word
# "Ticker" and will be matched by a naive search.
RESULTS_TABLE_CLASS = "screener_table"
_CHROME_TAGS = ("select", "option", "input", "textarea", "form")


def _looks_like_results_table(table: Any) -> bool:
    """True for a table that is the screener's result grid, not filter chrome."""
    classes = {str(name).lower() for name in (table.get("class") or [])}
    if RESULTS_TABLE_CLASS in classes:
        return True
    if table.find(_CHROME_TAGS):  # a filter widget, never the result grid
        return False
    rows = table.find_all("tr")
    if len(rows) < 2:
        return False
    headers = [cell.get_text(strip=True).lower() for cell in rows[0].find_all(["th", "td"])]
    if "ticker" not in headers:
        return False
    # The grid's body rows line up with its header; chrome tables do not.
    body_widths = {len(row.find_all("td")) for row in rows[1:] if row.find_all("td")}
    return bool(body_widths) and max(body_widths) >= len(headers) - 1


def parse_screener_html(html: str) -> list[dict[str, Any]]:
    """Parse the public screener's result grid; returns [] when it is absent.

    FinViz renders the filter UI as tables too, and its order-by ``<select>``
    contains the word "Ticker" — so the grid is identified by its
    ``screener_table`` class, with a structural fallback (a header row carrying a
    real ``Ticker`` column, no form controls, body rows as wide as the header).
    """
    if not HAS_BS4:
        raise FetchError(
            "public screener parsing needs beautifulsoup4. "
            "Install it (pip install -r requirements.txt), set FINVIZ_API_KEY "
            "for Elite export, or run with --fixture."
        )
    soup = BeautifulSoup(html, "html.parser")
    tables = [table for table in soup.find_all("table") if _looks_like_results_table(table)]

    for table in tables:
        all_rows = table.find_all("tr")
        header_cells = [cell.get_text(strip=True) for cell in all_rows[0].find_all(["th", "td"])]
        if not header_cells:
            continue
        rows: list[dict[str, Any]] = []
        for tr in all_rows[1:]:
            cells = [cell.get_text(strip=True) for cell in tr.find_all("td")]
            if len(cells) < 2:
                continue
            normalized = normalize_row(dict(zip(header_cells, cells)))
            ticker = normalized.get("ticker")
            # FinViz numbers its rows; a value that is not a symbol is chrome.
            if ticker and ticker.replace(".", "").replace("-", "").isalpha():
                rows.append(normalized)
        if rows:
            return rows
    return []


def fetch_view_rows(
    config: dict[str, Any],
    variant: str,
    view: str,
    *,
    mode: str,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Fetch every row for one (variant, view) pair across exchange passes."""
    spec = get_variant(config, variant)
    order = spec.get("order")
    delay = float(config["screener"].get("request_delay_seconds", 1.5))
    max_pages = int(config["screener"].get("max_pages", 2))
    rows: list[dict[str, Any]] = []

    for entry in build_variant_urls(config, variant):
        if entry["view"] != view:
            continue
        filters = entry["filters"]
        if mode == "elite":
            url = _export_url(config, filters, view, order)
            if verbose:
                print(f"  GET (elite export) v={VIEW_CODES[view]} {variant}", file=sys.stderr)
            rows.extend(parse_export_csv(_http_get(url)))
            time.sleep(delay)
            continue

        for page in range(max_pages):
            url = entry["url"] + (f"&r={page * ROWS_PER_PAGE + 1}" if page else "")
            if verbose:
                print(f"  GET (public) {url}", file=sys.stderr)
            page_rows = parse_screener_html(_http_get(url))
            rows.extend(page_rows)
            time.sleep(delay)
            if len(page_rows) < ROWS_PER_PAGE:
                break
    return rows


def merge_rows(row_sets: list[list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Merge per-view rows on ticker; later views only fill missing fields."""
    merged: dict[str, dict[str, Any]] = {}
    for rows in row_sets:
        for row in rows:
            ticker = row.get("ticker")
            if not ticker:
                continue
            target = merged.setdefault(ticker, {})
            for key, value in row.items():
                if value is not None and target.get(key) is None:
                    target[key] = value
    return merged


def _exchange_allowed(config: dict[str, Any], hit: dict[str, Any]) -> bool:
    allowed = {str(code).upper() for code in config["screener"].get("allowed_exchanges") or []}
    exchange = hit.get("exchange")
    if not allowed or not exchange:
        return True
    return str(exchange).upper() in allowed


def load_fixture(path: str, variant: str | None = None) -> list[dict[str, Any]]:
    """Load hits from a JSON fixture (list, or {"hits": [...]})."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    raw = data.get("hits", data) if isinstance(data, dict) else data
    if not isinstance(raw, list):
        raise FetchError(f"fixture {path} must be a list or contain a 'hits' list")
    hits = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if variant and item.get("variant") not in (None, variant):
            continue
        hit = dict(item)
        hit["ticker"] = str(hit.get("ticker", "")).strip().upper()
        if hit["ticker"]:
            hits.append(hit)
    return hits


def screen_variant(
    config: dict[str, Any],
    variant: str,
    *,
    mode: str | None = None,
    fixture: str | None = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Return normalized hits for *variant*."""
    spec = get_variant(config, variant)
    resolved = (mode or config["screener"].get("mode", "auto")).lower()
    if fixture:
        resolved = "fixture"
    elif resolved == "auto":
        resolved = "elite" if elite_mode(config) else "public"

    if resolved == "fixture":
        if not fixture:
            raise FetchError("--fixture is required in fixture mode")
        hits = load_fixture(fixture, variant=variant)
    else:
        row_sets = [
            fetch_view_rows(config, variant, view, mode=resolved, verbose=verbose)
            for view in variant_views(config, variant)
        ]
        hits = list(merge_rows(row_sets).values())

    out = []
    for hit in hits:
        hit.setdefault("asset_type", spec["asset_type"])
        hit["variant"] = variant
        hit["screen_mode"] = resolved
        hit.setdefault("filters", ",".join(variant_filters(config, variant)))
        if _exchange_allowed(config, hit):
            out.append(hit)
    return out


def screen_all(
    config: dict[str, Any],
    *,
    mode: str | None = None,
    fixture: str | None = None,
    variants: list[str] | None = None,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    """Screen every configured variant, de-duplicated by (ticker, variant)."""
    names = variants or list(config["screener"]["variants"])
    seen: set[tuple[str, str]] = set()
    hits: list[dict[str, Any]] = []
    for name in names:
        for hit in screen_variant(config, name, mode=mode, fixture=fixture, verbose=verbose):
            key = (hit["ticker"], name)
            if key in seen:
                continue
            seen.add(key)
            hits.append(hit)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch lowcap screener hits")
    parser.add_argument("--config")
    parser.add_argument("--variant", help="One variant (default: all)")
    parser.add_argument("--mode", choices=["auto", "elite", "public", "fixture"], default=None)
    parser.add_argument("--fixture", help="JSON fixture of hits (offline)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    try:
        hits = screen_all(
            config,
            mode=args.mode,
            fixture=args.fixture,
            variants=[args.variant] if args.variant else None,
            verbose=args.verbose,
        )
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(hits, indent=2, sort_keys=True))
        return 0
    print(f"{len(hits)} hit(s)")
    for hit in hits:
        print(
            f"  {hit['ticker']:<6} {hit.get('asset_type', '?'):<5} "
            f"{hit['variant']:<18} price={hit.get('price')} "
            f"chg={hit.get('change_pct')} relvol={hit.get('rel_volume')} "
            f"short={hit.get('short_float_pct')} float={hit.get('float_shares')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
