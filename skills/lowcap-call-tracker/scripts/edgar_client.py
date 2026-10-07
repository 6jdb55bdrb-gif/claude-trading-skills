#!/usr/bin/env python3
"""A small, polite SEC EDGAR client for the explosion-signals layer.

EDGAR is free and needs no key, but it has conditions of use: every request
must declare a User-Agent naming a real contact, and traffic is capped at 10
requests per second. Those are enforced here rather than left to each caller:

* with no User-Agent configured the client is **disabled and sends nothing**.
  An anonymous request is a policy breach even when it would have worked, and
  a tracker that quietly breached it would eventually get the operator's IP
  blocked mid-run.
* every request passes through one rate limiter, below the published ceiling.

Set the contact in ``explosion_signals.edgar.user_agent`` or in the
``EDGAR_USER_AGENT`` environment variable, e.g.
``lowcap-tracker you@example.com``.

Endpoints used (all public, all JSON):
    https://www.sec.gov/files/company_tickers.json       ticker -> CIK
    https://data.sec.gov/submissions/CIK##########.json  filing index
    https://data.sec.gov/api/xbrl/companyconcept/...     cash and cash flow
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timezone
from typing import Any, Callable

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
CONCEPT_URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"

# SEC publishes 10/second; the default config asks for 8 to leave headroom.
MAX_RATE = 10.0

CASH_CONCEPTS = (
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
)
BURN_CONCEPT = "NetCashProvidedByUsedInOperatingActivities"


def _parse_moment(raw: Any) -> datetime | None:
    """Parse an EDGAR timestamp or date into an aware datetime, or None."""
    if not raw:
        return None
    text = str(raw).strip().replace("Z", "+00:00")
    for candidate in (text, text.split("T")[0]):
        try:
            moment = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    return None


def hours_since(raw: Any, *, now: Any = None) -> float | None:
    """Hours between an EDGAR acceptance timestamp and *now*, or None."""
    moment = _parse_moment(raw)
    if moment is None:
        return None
    reference = _parse_moment(now) or datetime.now(timezone.utc)
    return (reference - moment).total_seconds() / 3600.0


def days_since(raw: Any, *, as_of: Any = None) -> int | None:
    moment = _parse_moment(raw)
    if moment is None:
        return None
    reference = _parse_moment(as_of) or datetime.now(timezone.utc)
    return int((reference.date() - moment.date()).days)


class EdgarClient:
    """Rate-limited JSON fetcher, disabled until a contact is declared."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        transport: Callable[[str, dict[str, str]], Any] | None = None,
        version: str | None = None,
    ) -> None:
        from explosion_signals import edgar_settings

        settings = edgar_settings(config, version)
        self.user_agent = str(
            os.environ.get("EDGAR_USER_AGENT") or settings.get("user_agent") or ""
        ).strip()
        rate = settings.get("max_requests_per_second")
        try:
            self.rate = min(float(rate), MAX_RATE) if rate else 8.0
        except (TypeError, ValueError):
            self.rate = 8.0
        self.timeout = int(settings.get("timeout_seconds") or 15)
        self._transport = transport
        self._last_request = 0.0
        self._cache: dict[str, Any] = {}

        if not self.user_agent:
            self.available = False
            self.reason = (
                "EDGAR needs a contact: set explosion_signals.edgar.user_agent "
                "or EDGAR_USER_AGENT (e.g. 'lowcap-tracker you@example.com')"
            )
        elif "@" not in self.user_agent:
            # SEC asks for a contact, and a bare tool name is exactly what the
            # fair-access policy exists to stop.
            self.available = False
            self.reason = (
                f"EDGAR user_agent {self.user_agent!r} names no contact: SEC fair access "
                "asks for an email address in the User-Agent"
            )
        else:
            self.available = True
            self.reason = ""

    def _wait(self) -> None:
        gap = 1.0 / self.rate if self.rate > 0 else 0.0
        elapsed = time.monotonic() - self._last_request
        if self._last_request and elapsed < gap:
            time.sleep(gap - elapsed)
        self._last_request = time.monotonic()

    def get_json(self, url: str) -> Any:
        """Fetch and decode *url*, or None on any failure. Never raises."""
        if not self.available:
            return None
        if url in self._cache:
            return self._cache[url]
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        self._wait()
        try:
            if self._transport is not None:
                payload = self._transport(url, headers)
            else:  # pragma: no cover - network path
                import requests

                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            # A provider outage must never reach the Judge as a number, and
            # must never take the cycle down. The signal records n/a instead.
            return None
        if isinstance(payload, (str, bytes)):
            try:
                payload = json.loads(payload)
            except ValueError:
                return None
        self._cache[url] = payload
        return payload

    def cik_for(self, ticker: str) -> str | None:
        """The zero-padded CIK for *ticker*, or None."""
        payload = self.get_json(TICKER_MAP_URL)
        if not isinstance(payload, dict):
            return None
        wanted = str(ticker).strip().upper()
        rows = payload.values() if "0" in payload or not payload.get("data") else payload["data"]
        for row in rows:
            if isinstance(row, dict) and str(row.get("ticker", "")).upper() == wanted:
                return str(row.get("cik_str") or row.get("cik") or "").zfill(10)
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                if str(row[1]).upper() == wanted:
                    return str(row[0]).zfill(10)
        return None

    def submissions(self, ticker: str) -> Any:
        cik = self.cik_for(ticker)
        if not cik:
            return None
        return self.get_json(SUBMISSIONS_URL.format(cik=cik))

    def concept(self, ticker: str, concept: str) -> Any:
        cik = self.cik_for(ticker)
        if not cik:
            return None
        return self.get_json(CONCEPT_URL.format(cik=cik, concept=concept))


def _recent_rows(submissions: Any) -> list[dict[str, Any]]:
    """Flatten EDGAR's column-oriented ``filings.recent`` into rows."""
    if not isinstance(submissions, dict):
        return []
    recent = ((submissions.get("filings") or {}).get("recent")) or {}
    forms = recent.get("form") or []
    if not isinstance(forms, list):
        return []

    def at(key: str, index: int) -> Any:
        column = recent.get(key)
        if isinstance(column, list) and index < len(column):
            return column[index]
        return None

    rows = []
    for index, form in enumerate(forms):
        rows.append(
            {
                "form": str(form or "").upper(),
                "filingDate": at("filingDate", index),
                "accepted": at("acceptanceDateTime", index) or at("filingDate", index),
                "description": at("primaryDocDescription", index),
                "items": at("items", index),
            }
        )
    return rows


def latest_material_filing(submissions: Any, *, form_types: list[str]) -> dict[str, Any] | None:
    """The newest filing whose form is in *form_types*."""
    wanted = {str(form).upper() for form in form_types or []}
    rows = [row for row in _recent_rows(submissions) if row["form"] in wanted]
    if not rows:
        return None
    # EDGAR returns newest first, but sort rather than trust the order.
    rows.sort(key=lambda row: str(row.get("accepted") or ""), reverse=True)
    return rows[0]


def classify_filings(
    submissions: Any, *, form_types: list[str], as_of: Any = None
) -> list[dict[str, Any]]:
    """Every filing in *form_types*, with how many days ago it was filed."""
    wanted = {str(form).upper() for form in form_types or []}
    out = []
    for row in _recent_rows(submissions):
        if row["form"] not in wanted:
            continue
        age = days_since(row.get("filingDate") or row.get("accepted"), as_of=as_of)
        if age is None:
            continue
        out.append({"form": row["form"], "days_ago": age, "accepted": row.get("accepted")})
    return out


def form4_purchases(rows: list[dict[str, Any]], *, codes: list[str]) -> int | None:
    """Days since the most recent open-market purchase, or None if there is none.

    Form 4 transaction code ``P`` is a purchase. An award (``A``) or an option
    exercise (``M``) is not someone spending their own money, and counting
    either as insider conviction is how a grant becomes a buy signal.
    """
    wanted = {str(code).upper() for code in codes or []}
    ages = [
        age
        for row in rows or []
        if (age := row.get("days_ago")) is not None
        and wanted & {str(code).upper() for code in row.get("transaction_codes") or []}
    ]
    return min(ages) if ages else None


def months_of_runway(*, cash: Any, quarterly_operating_cash_flow: Any) -> float | None:
    """Months of cash at the latest quarter's burn rate.

    A company generating cash has no runway to run out of, so it returns
    infinity rather than a number that would read as "about to die".
    """
    try:
        cash_value = None if cash is None else float(cash)
        flow = (
            None if quarterly_operating_cash_flow is None else float(quarterly_operating_cash_flow)
        )
    except (TypeError, ValueError):
        return None
    if cash_value is None or flow is None:
        return None
    if flow >= 0:
        return float("inf")
    monthly_burn = abs(flow) / 3.0
    if monthly_burn <= 0:
        return float("inf")
    return round(cash_value / monthly_burn, 1)


def today_iso() -> str:
    return date.today().isoformat()
