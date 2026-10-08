#!/usr/bin/env python3
"""Measurement for the explosion-signals layer: the facts, not the scoring.

Each public function here takes already-fetched rows and returns a number or
``None``. The network wrappers are thin shells around them, so the arithmetic
is testable offline and a provider outage can only ever produce ``None`` —
which the scorer reads as "n/a", scoring nothing.

Sources, all free and keyless:

* **yfinance** — intraday bars (VWAP, premarket), daily bars (range
  contraction), split history (reverse splits).
* **iBorrowDesk** (``iborrowdesk.com/api/ticker/<SYM>``) — borrow fee.
* **Nasdaq Trader** (``nasdaqtrader.com/rss.aspx?feed=tradehalts``) — halts.
* **FinViz** — one screen of today's >10% movers, for sector sympathy.
* **SEC EDGAR** — filings, Form 4s, cash and burn (see ``edgar_client``).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

IBORROWDESK_URL = "https://iborrowdesk.com/api/ticker/{ticker}"
HALT_FEED_URL = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts"

# US regular session in Eastern time; a bar before this is premarket.
REGULAR_OPEN_MINUTES = 9 * 60 + 30
REGULAR_CLOSE_MINUTES = 16 * 60


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("%", "").replace(",", "").replace("+", "")
        if not text or text in {"-", "--", "n/a", "N/A"}:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
    return number if number == number and abs(number) != float("inf") else None


def _minute_of_day(stamp: Any) -> int | None:
    """Minutes past midnight for a bar timestamp, or None."""
    text = str(stamp or "").strip()
    match = re.search(r"(\d{1,2}):(\d{2})", text)
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


# --- VWAP ---------------------------------------------------------------


def session_vwap(bars: list[dict[str, Any]] | None) -> float | None:
    """Volume-weighted average price over *bars*, using each bar's typical price.

    Volume-weighted, not an average of closes: one large print near the low is
    where the day's real average sits, and that is the line traders defend.
    """
    if not bars:
        return None
    turnover = 0.0
    volume_total = 0.0
    for candle in bars:
        volume = _number(candle.get("volume")) or 0.0
        if volume <= 0:
            continue
        high = _number(candle.get("high"))
        low = _number(candle.get("low"))
        close = _number(candle.get("close"))
        if close is None and (high is None or low is None):
            continue
        typical = close if (high is None or low is None) else (high + low + (close or high)) / 3.0
        turnover += typical * volume
        volume_total += volume
    if volume_total <= 0:
        return None
    return round(turnover / volume_total, 4)


# --- premarket ----------------------------------------------------------


def premarket_stats(
    bars: list[dict[str, Any]] | None, *, prior_close: Any, avg_volume: Any
) -> dict[str, Any]:
    """The premarket gap and how much volume paid for it."""
    out: dict[str, Any] = {"premarket_gap_pct": None, "premarket_volume_pct_of_adv": None}
    pre = []
    for candle in bars or []:
        minute = _minute_of_day(candle.get("datetime") or candle.get("date"))
        if minute is None or minute >= REGULAR_OPEN_MINUTES:
            continue
        pre.append(candle)
    if not pre:
        return out

    last_close = _number(pre[-1].get("close"))
    base = _number(prior_close)
    if last_close is not None and base and base > 0:
        out["premarket_gap_pct"] = round((last_close / base - 1.0) * 100.0, 2)
    volume = sum(_number(candle.get("volume")) or 0.0 for candle in pre)
    adv = _number(avg_volume)
    if adv and adv > 0:
        out["premarket_volume_pct_of_adv"] = round(100.0 * volume / adv, 2)
    out["premarket_volume"] = volume
    return out


# --- volatility contraction ---------------------------------------------


def range_percentile(
    bars: list[dict[str, Any]] | None, *, window: int = 10, lookback: int = 60
) -> float | None:
    """Where the latest *window*-session range sits in its own *lookback* history.

    A rolling high-low range rather than a Bollinger width: it needs no moving
    average to warm up, so it answers on 60 bars instead of 80, and on a $1.20
    lowcap it is the same measurement.
    """
    rows = [candle for candle in (bars or []) if _number(candle.get("high")) is not None]
    if len(rows) < window:
        return None
    rows = rows[-lookback:]
    ranges = []
    for end in range(window, len(rows) + 1):
        chunk = rows[end - window : end]
        highs = [_number(candle.get("high")) for candle in chunk]
        lows = [_number(candle.get("low")) for candle in chunk]
        highs = [value for value in highs if value is not None]
        lows = [value for value in lows if value is not None]
        if not highs or not lows:
            continue
        top, bottom = max(highs), min(lows)
        mid = (top + bottom) / 2.0
        # Normalised by price so a $1 and a $19 name are comparable.
        ranges.append((top - bottom) / mid * 100.0 if mid > 0 else 0.0)
    if not ranges:
        return None
    current = ranges[-1]
    at_or_below = sum(1 for value in ranges if value <= current)
    return round(100.0 * at_or_below / len(ranges), 1)


# --- borrow fee ---------------------------------------------------------


def borrow_fee_from_iborrowdesk(payload: Any) -> float | None:
    """The newest borrow fee in an iBorrowDesk ticker payload."""
    if not isinstance(payload, dict):
        return None
    rows = payload.get("daily") or payload.get("real_time") or []
    if not isinstance(rows, list) or not rows:
        return None
    dated = [row for row in rows if isinstance(row, dict)]
    dated.sort(key=lambda row: str(row.get("date") or row.get("time") or ""))
    for row in reversed(dated):
        fee = _number(row.get("fee"))
        if fee is not None:
            return fee
    return None


# --- halts --------------------------------------------------------------


def count_halts(feed_xml: Any, ticker: str, *, as_of: str | None = None) -> int | None:
    """How many times *ticker* was halted on *as_of*, or None if unreadable.

    Zero is a real answer here: the feed was read and this symbol is not in
    it. Only an unreadable feed is unknown.
    """
    if not feed_xml or not isinstance(feed_xml, str):
        return None
    if "<item" not in feed_xml and "<rss" not in feed_xml:
        return None
    today = as_of or date.today().isoformat()
    try:
        year, month, day = today.split("-")
        wanted_date = f"{int(month):02d}/{int(day):02d}/{year}"
    except (ValueError, AttributeError):
        return None
    wanted = str(ticker).strip().upper()
    items = re.findall(r"<item>(.*?)</item>", feed_xml, flags=re.S)
    if not items:
        return None
    count = 0
    for item in items:
        symbol = re.search(r"IssueSymbol[^>]*>([^<]+)<", item)
        halted = re.search(r"HaltDate[^>]*>([^<]+)<", item)
        if not symbol or str(symbol.group(1)).strip().upper() != wanted:
            continue
        if halted and str(halted.group(1)).strip() != wanted_date:
            continue
        count += 1
    return count


# --- reverse split ------------------------------------------------------


def reverse_split_age(splits: Any, *, as_of: str | None = None) -> int | None:
    """Days since the most recent reverse split, or None if there is none.

    A reverse split is a ratio below 1 (a 1-for-10 reports as 0.1). A forward
    split is not one, and an absent history is unknown rather than clean —
    which is why the hard skip refuses to fire on None.
    """
    if not splits or not isinstance(splits, dict):
        return None
    reference = date.fromisoformat(as_of) if as_of else date.today()
    ages = []
    for raw_date, raw_ratio in splits.items():
        ratio = _number(raw_ratio)
        if ratio is None or ratio >= 1.0:
            continue
        text = str(raw_date).split("T")[0].split(" ")[0]
        try:
            when = date.fromisoformat(text)
        except ValueError:
            continue
        ages.append((reference - when).days)
    return min(ages) if ages else None


# --- sector sympathy ----------------------------------------------------


def peer_count_from_rows(
    movers: list[dict[str, Any]] | None, *, ticker: str, industry: Any, min_change: float
) -> int | None:
    """How many OTHER names in *industry* are up more than *min_change* today."""
    if movers is None or not industry:
        return None
    wanted = str(industry).strip().lower()
    self_ticker = str(ticker).strip().upper()
    count = 0
    for row in movers:
        if str(row.get("ticker", "")).strip().upper() == self_ticker:
            # Counting yourself would turn every lone runner into a theme.
            continue
        if str(row.get("industry", "")).strip().lower() != wanted:
            continue
        change = _number(row.get("change_pct"))
        if change is not None and change > min_change:
            count += 1
    return count


# --- the network wrappers ----------------------------------------------


def _http_text(url: str, *, timeout: int = 15) -> str | None:
    try:  # pragma: no cover - network path
        import requests

        response = requests.get(url, timeout=timeout, headers={"User-Agent": "lowcap-call-tracker"})
        response.raise_for_status()
        return response.text
    except Exception:
        return None


def _http_json(url: str, *, timeout: int = 15) -> Any:
    try:  # pragma: no cover - network path
        import requests

        response = requests.get(url, timeout=timeout, headers={"User-Agent": "lowcap-call-tracker"})
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _intraday_bars(ticker: str) -> tuple[list[dict[str, Any]], float | None]:
    """Today's 5-minute bars including premarket, plus the prior close."""
    try:  # pragma: no cover - network path
        import yfinance
    except ImportError:
        return [], None
    try:  # pragma: no cover - network path
        frame = yfinance.Ticker(ticker).history(
            period="2d", interval="5m", prepost=True, auto_adjust=False
        )
    except Exception:
        return [], None
    bars: list[dict[str, Any]] = []
    for index, row in frame.iterrows():  # pragma: no cover - network path
        bars.append(
            {
                "datetime": str(index),
                "date": str(index)[:10],
                "high": _number(row.get("High")),
                "low": _number(row.get("Low")),
                "close": _number(row.get("Close")),
                "volume": _number(row.get("Volume")),
            }
        )
    if not bars:
        return [], None
    today = bars[-1]["date"]
    prior = [candle for candle in bars if candle["date"] < today]
    prior_close = None
    for candle in reversed(prior):  # pragma: no cover - network path
        minute = _minute_of_day(candle["datetime"])
        if minute is not None and minute <= REGULAR_CLOSE_MINUTES and candle["close"]:
            prior_close = candle["close"]
            break
    return [candle for candle in bars if candle["date"] == today], prior_close


def _daily_bars(ticker: str, *, lookback: int = 60) -> list[dict[str, Any]]:
    try:  # pragma: no cover - network path
        import yfinance
    except ImportError:
        return []
    try:  # pragma: no cover - network path
        frame = yfinance.Ticker(ticker).history(
            period=f"{max(lookback * 2, 120)}d", interval="1d", auto_adjust=False
        )
    except Exception:
        return []
    return [  # pragma: no cover - network path
        {
            "date": str(index.date()),
            "high": _number(row.get("High")),
            "low": _number(row.get("Low")),
            "close": _number(row.get("Close")),
        }
        for index, row in frame.iterrows()
    ]


def _splits(ticker: str) -> dict[str, Any] | None:
    try:  # pragma: no cover - network path
        import yfinance

        series = yfinance.Ticker(ticker).splits
    except Exception:
        return None
    try:  # pragma: no cover - network path
        return {str(index.date()): float(value) for index, value in series.items()}
    except Exception:
        return None


def fetch_movers(
    config: dict[str, Any], *, min_change: float = 10.0
) -> list[dict[str, Any]] | None:
    """One FinViz screen of today's big movers, for the sector-sympathy count.

    A single request per cycle, shared by every hit: asking per name would be
    one request per ticker for the same answer.
    """
    try:
        from fetch_screener import fetch_rows_for_filters
    except ImportError:  # pragma: no cover - defensive
        return None
    try:
        return fetch_rows_for_filters(
            config,
            filters=["geo_usa", "ind_stocksonly", f"ta_change_u{int(min_change)}"],
            view="overview",
        )
    except Exception:
        return None


def premarket_moves(
    tickers: dict[str, Any], *, as_of: str | None = None
) -> dict[str, dict[str, Any]]:
    """Measure the pre-market gap and volume share for many names at once.

    *tickers* maps ticker to its average daily volume (from the screener row),
    which is what the volume share is measured against. One batched download
    rather than one request per name: the pre-market screen looks at dozens of
    names and has a session's worth of time to do it in.

    A name with no pre-market print is simply absent from the result — most of
    the universe has none, and that is not a finding.
    """
    if not tickers:
        return {}
    try:  # pragma: no cover - network path
        import yfinance
    except ImportError:
        return {}
    symbols = sorted(name for name in tickers if name)
    try:  # pragma: no cover - network path
        data = yfinance.download(
            tickers=" ".join(symbols),
            period="2d",
            interval="5m",
            prepost=True,
            progress=False,
            group_by="ticker",
            auto_adjust=False,
            threads=False,
        )
    except Exception:
        return {}
    if data is None or getattr(data, "empty", True):  # pragma: no cover - network path
        return {}

    out: dict[str, dict[str, Any]] = {}
    for symbol in symbols:  # pragma: no cover - network path
        try:
            frame = data[symbol] if len(symbols) > 1 else data
        except (KeyError, TypeError):
            continue
        bars = []
        for index, row in frame.iterrows():
            close = _number(row.get("Close"))
            if close is None:
                continue
            bars.append(
                {
                    "datetime": str(index),
                    "date": str(index)[:10],
                    "high": _number(row.get("High")),
                    "low": _number(row.get("Low")),
                    "close": close,
                    "volume": _number(row.get("Volume")),
                }
            )
        if not bars:
            continue
        today = as_of or bars[-1]["date"]
        prior_close = None
        for candle in reversed([bar for bar in bars if bar["date"] < today]):
            minute = _minute_of_day(candle["datetime"])
            if minute is not None and minute <= REGULAR_CLOSE_MINUTES:
                prior_close = candle["close"]
                break
        stats = premarket_stats(
            [bar for bar in bars if bar["date"] == today],
            prior_close=prior_close,
            avg_volume=tickers.get(symbol),
        )
        if stats.get("premarket_gap_pct") is None:
            continue
        last = None
        for candle in reversed([bar for bar in bars if bar["date"] == today]):
            if _minute_of_day(candle["datetime"]) is not None:
                last = candle["close"]
                break
        out[symbol] = {
            "gap_pct": stats["premarket_gap_pct"],
            "volume_pct_of_adv": stats.get("premarket_volume_pct_of_adv"),
            "last": last,
            "prior_close": prior_close,
        }
    return out


def gather_signal_data(
    hit: dict[str, Any],
    config: dict[str, Any],
    *,
    offline: bool = False,
    movers: list[dict[str, Any]] | None = None,
    edgar: Any = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Measure everything the scorer needs for one hit.

    Returns a flat sheet of facts, with ``None`` wherever a source could not be
    read. Nothing in here raises: a provider failure is a missing number, not
    a failed cycle.
    """
    from explosion_signals import signals_config, signals_enabled
    from screener_guards import hit_version

    version = hit_version(hit, config)
    if not signals_enabled(config, version):
        return {}

    block = signals_config(config, version)
    ticker = str(hit.get("ticker") or "").upper()
    today = as_of or date.today().isoformat()
    data: dict[str, Any] = {
        "offline": bool(offline),
        "notes": [],
        "vwap": None,
        "premarket_gap_pct": None,
        "premarket_volume_pct_of_adv": None,
        "range_percentile": None,
        "borrow_fee_pct": None,
        "catalyst_hours_ago": None,
        "catalyst_form": None,
        "catalyst_found": None,
        "news_hours_ago": None,
        "insider_buy_days_ago": None,
        "insider_checked": False,
        "sector_peers_up": None,
        "dilution_filings": None,
        "reverse_split_days_ago": None,
        "cash_runway_months": None,
        "halts_today": None,
    }
    if hit.get("catalyst_headline"):
        # Read off the screener row, so it survives an offline run: FinViz only
        # carries a headline while it is current, which makes its presence the
        # freshness signal. Treated as a same-session item and never back-dated
        # into precision it does not have.
        data["news_hours_ago"] = 12.0

    if offline:
        data["notes"].append("offline: every network-backed signal reports n/a")
        return data

    signals = block.get("signals") or {}
    skips = block.get("hard_skips") or {}

    # --- intraday: VWAP and the premarket gap, from one download ---------
    if (signals.get("vwap_position", {}).get("enabled", True)) or (
        signals.get("premarket_gap", {}).get("enabled", True)
    ):
        bars, prior_close = _intraday_bars(ticker)
        if bars:
            data["vwap"] = session_vwap([candle for candle in bars if _is_regular(candle)] or bars)
            data.update(
                {
                    key: value
                    for key, value in premarket_stats(
                        bars, prior_close=prior_close, avg_volume=hit.get("avg_volume")
                    ).items()
                    if key in data or key == "premarket_volume"
                }
            )
        else:
            data["notes"].append(f"{ticker}: no intraday bars (VWAP and premarket n/a)")

    # --- daily history: the range percentile -----------------------------
    spec = signals.get("volatility_contraction") or {}
    if spec.get("enabled", True):
        lookback = int(_number(spec.get("lookback_days")) or 60)
        window = int(_number(spec.get("range_days")) or 10)
        daily = _daily_bars(ticker, lookback=lookback)
        data["range_percentile"] = range_percentile(daily, window=window, lookback=lookback)
        if data["range_percentile"] is None:
            data["notes"].append(f"{ticker}: not enough daily history for the range percentile")

    # --- borrow fee ------------------------------------------------------
    if (signals.get("short_squeeze_pressure") or {}).get("enabled", True):
        data["borrow_fee_pct"] = borrow_fee_from_iborrowdesk(
            _http_json(IBORROWDESK_URL.format(ticker=ticker))
        )

    # --- halts -----------------------------------------------------------
    if (skips.get("intraday_halts") or {}).get("enabled", True):
        data["halts_today"] = count_halts(_http_text(HALT_FEED_URL), ticker, as_of=today)

    # --- reverse split ---------------------------------------------------
    if (skips.get("reverse_split") or {}).get("enabled", True):
        data["reverse_split_days_ago"] = reverse_split_age(_splits(ticker), as_of=today)

    # --- sector sympathy --------------------------------------------------
    spec = signals.get("sector_sympathy") or {}
    if spec.get("enabled", True):
        threshold = _number(spec.get("peer_min_change_pct")) or 10.0
        rows = movers if movers is not None else fetch_movers(config, min_change=threshold)
        data["sector_peers_up"] = peer_count_from_rows(
            rows, ticker=ticker, industry=hit.get("industry"), min_change=threshold
        )

    _gather_edgar(data, hit, config, version, edgar=edgar, as_of=today)
    return data


def _is_regular(candle: dict[str, Any]) -> bool:
    minute = _minute_of_day(candle.get("datetime") or candle.get("date"))
    return minute is not None and REGULAR_OPEN_MINUTES <= minute <= REGULAR_CLOSE_MINUTES


def _gather_edgar(
    data: dict[str, Any],
    hit: dict[str, Any],
    config: dict[str, Any],
    version: str,
    *,
    edgar: Any = None,
    as_of: str,
) -> None:
    """Fill the EDGAR-backed facts, or leave them None and say why."""
    from edgar_client import (
        EdgarClient,
        classify_filings,
        hours_since,
        latest_material_filing,
        months_of_runway,
    )
    from explosion_signals import signals_config

    client = edgar
    if client is None:
        client = EdgarClient(config, version=version)
    if not getattr(client, "available", False):
        data["notes"].append(getattr(client, "reason", "EDGAR unavailable"))
        return

    ticker = str(hit.get("ticker") or "").upper()
    submissions = client.submissions(ticker)
    if submissions is None:
        data["notes"].append(f"{ticker}: no EDGAR submissions index")
        return

    block = signals_config(config, version)
    signals = block.get("signals") or {}
    skips = block.get("hard_skips") or {}

    spec = signals.get("catalyst_recency") or {}
    if spec.get("enabled", True):
        filing = latest_material_filing(submissions, form_types=spec.get("form_types") or ["8-K"])
        # The index was read, so "nothing material on file" is a fact now.
        data["catalyst_found"] = bool(filing)
        if filing:
            data["catalyst_form"] = filing.get("form")
            data["catalyst_hours_ago"] = hours_since(filing.get("accepted"))

    spec = signals.get("insider_buying") or {}
    if spec.get("enabled", True):
        # Form 4 transaction codes live inside each filing's own document, and
        # fetching one document per Form 4 per hit would blow through the rate
        # limit for a 5-point signal. The index gives the dates; a filing is
        # counted only when its description names a purchase.
        rows = []
        for row in classify_filings(submissions, form_types=["4"], as_of=as_of):
            rows.append({**row, "transaction_codes": ["P"] if _looks_like_purchase(row) else []})
        data["insider_checked"] = True
        from edgar_client import form4_purchases

        data["insider_buy_days_ago"] = form4_purchases(
            rows, codes=spec.get("transaction_codes") or ["P"]
        )

    spec = skips.get("dilution_filings") or {}
    if spec.get("enabled", True):
        data["dilution_filings"] = classify_filings(
            submissions, form_types=spec.get("form_types") or [], as_of=as_of
        )

    spec = skips.get("cash_runway") or {}
    if spec.get("enabled", True):
        data["cash_runway_months"] = months_of_runway(
            cash=_latest_concept_value(client, ticker, _cash_concepts()),
            quarterly_operating_cash_flow=_latest_concept_value(client, ticker, [_burn_concept()]),
        )
        if data["cash_runway_months"] is None:
            data["notes"].append(f"{ticker}: no 10-Q cash or burn figures on EDGAR")


def _looks_like_purchase(row: dict[str, Any]) -> bool:
    """Whether a Form 4 index row reads as an open-market purchase.

    Deliberately conservative: the index description is all that is available
    without a second request per filing, so anything ambiguous counts as "not
    a purchase" and the signal simply does not pay.
    """
    text = " ".join(str(row.get(key) or "") for key in ("description", "form")).lower()
    return "purchase" in text or "acquisition" in text


def _cash_concepts() -> list[str]:
    from edgar_client import CASH_CONCEPTS

    return list(CASH_CONCEPTS)


def _burn_concept() -> str:
    from edgar_client import BURN_CONCEPT

    return BURN_CONCEPT


def _latest_concept_value(client: Any, ticker: str, concepts: list[str]) -> float | None:
    """The newest reported value for the first concept that has one."""
    for concept in concepts:
        payload = client.concept(ticker, concept)
        if not isinstance(payload, dict):
            continue
        units = payload.get("units") or {}
        rows = []
        for entries in units.values():
            if isinstance(entries, list):
                rows.extend(entry for entry in entries if isinstance(entry, dict))
        quarterly = [row for row in rows if str(row.get("form", "")).startswith("10-Q")] or rows
        quarterly.sort(key=lambda row: str(row.get("end") or ""))
        for row in reversed(quarterly):
            value = _number(row.get("val"))
            if value is not None:
                return value
    return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
