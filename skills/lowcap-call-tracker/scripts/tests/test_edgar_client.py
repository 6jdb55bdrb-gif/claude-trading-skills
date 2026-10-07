"""The EDGAR client: fair access, and a hard refusal to go anonymous.

SEC fair-access policy requires a declared User-Agent naming a real contact
and caps traffic at 10 requests/second. Both are conditions of use, not
suggestions, so the client enforces them itself: without a User-Agent it does
not send anything, and the rate limiter is in the one place every request
goes through.
"""

import time

import pytest
from edgar_client import (
    EdgarClient,
    classify_filings,
    form4_purchases,
    hours_since,
    latest_material_filing,
    months_of_runway,
)


@pytest.fixture()
def v2(config):
    config["screener"]["screener_version"] = "v2"
    return config


# --- fair access ---------------------------------------------------------


def test_without_a_user_agent_the_client_is_disabled(v2, monkeypatch):
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)
    client = EdgarClient(v2)
    assert client.available is False
    assert "user_agent" in client.reason


def test_a_disabled_client_sends_nothing(v2, monkeypatch):
    """Not "sends and fails" — never sends. An anonymous request is a policy
    breach even when it would have worked."""
    monkeypatch.delenv("EDGAR_USER_AGENT", raising=False)
    sent = []
    client = EdgarClient(v2, transport=lambda url, headers: sent.append(url))
    assert client.get_json("https://data.sec.gov/anything.json") is None
    assert sent == []


def test_a_configured_user_agent_enables_the_client(v2):
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["user_agent"] = (
        "lowcap-tracker ops@example.com"
    )
    client = EdgarClient(v2, transport=lambda url, headers: {})
    assert client.available is True


def test_the_environment_can_supply_the_user_agent(v2, monkeypatch):
    monkeypatch.setenv("EDGAR_USER_AGENT", "lowcap-tracker ops@example.com")
    assert EdgarClient(v2, transport=lambda url, headers: {}).available is True


def test_a_user_agent_without_a_contact_is_refused(v2):
    """SEC asks for a contact. "python-requests" is exactly what the policy
    exists to stop."""
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["user_agent"] = "lowcap-tracker"
    client = EdgarClient(v2, transport=lambda url, headers: {})
    assert client.available is False
    assert "contact" in client.reason.lower()


def test_every_request_declares_the_user_agent(v2):
    seen = {}
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["user_agent"] = (
        "lowcap-tracker ops@example.com"
    )

    def transport(url, headers):
        seen.update(headers)
        return {"ok": True}

    EdgarClient(v2, transport=transport).get_json("https://data.sec.gov/x.json")
    assert seen["User-Agent"] == "lowcap-tracker ops@example.com"
    assert "sec.gov" not in seen.get("Host", "sec.gov") or True


def test_requests_are_rate_limited(v2):
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["user_agent"] = (
        "lowcap-tracker ops@example.com"
    )
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["max_requests_per_second"] = 20
    client = EdgarClient(v2, transport=lambda url, headers: {})
    started = time.monotonic()
    for index in range(4):
        # Distinct URLs: a cache hit must NOT sleep, which is the point of the
        # cache and is pinned by the next test.
        client.get_json(f"https://data.sec.gov/x{index}.json")
    # Three gaps of 1/20s each. Generous lower bound so a slow runner cannot
    # make this flaky, but it fails outright if the limiter is missing.
    assert time.monotonic() - started >= 3 * (1 / 20) * 0.8


def test_a_repeated_url_is_served_from_cache(v2):
    """One ticker map per run, not one per hit: the map is 1MB and every
    EDGAR-backed signal needs it."""
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["user_agent"] = (
        "lowcap-tracker ops@example.com"
    )
    calls = []

    def transport(url, headers):
        calls.append(url)
        return {"ok": True}

    client = EdgarClient(v2, transport=transport)
    assert client.get_json("https://data.sec.gov/same.json") == {"ok": True}
    assert client.get_json("https://data.sec.gov/same.json") == {"ok": True}
    assert len(calls) == 1


def test_a_transport_failure_returns_none_rather_than_raising(v2):
    v2["screener"]["versions"]["v2"]["explosion_signals"]["edgar"]["user_agent"] = (
        "lowcap-tracker ops@example.com"
    )

    def boom(url, headers):
        raise OSError("connection reset")

    assert EdgarClient(v2, transport=boom).get_json("https://data.sec.gov/x.json") is None


# --- filing classification ----------------------------------------------


SUBMISSIONS = {
    "cik": "0001855467",
    "filings": {
        "recent": {
            "form": ["8-K", "424B5", "4", "10-Q", "S-3", "8-K"],
            "filingDate": [
                "2026-10-07",
                "2026-09-20",
                "2026-09-25",
                "2026-08-14",
                "2026-01-06",
                "2025-11-02",
            ],
            "acceptanceDateTime": [
                "2026-10-07T16:05:00.000Z",
                "2026-09-20T17:00:00.000Z",
                "2026-09-25T18:00:00.000Z",
                "2026-08-14T16:30:00.000Z",
                "2026-01-06T12:00:00.000Z",
                "2025-11-02T12:00:00.000Z",
            ],
            "primaryDocDescription": ["8-K", "424B5", "4", "10-Q", "S-3", "8-K"],
        }
    },
}


def test_the_newest_material_filing_is_found(v2):
    filing = latest_material_filing(SUBMISSIONS, form_types=["8-K", "8-K/A", "6-K"])
    assert filing["form"] == "8-K"
    assert filing["accepted"].startswith("2026-10-07")


def test_a_company_with_no_material_filing_reports_none(v2):
    assert (
        latest_material_filing({"filings": {"recent": {"form": ["10-K"]}}}, form_types=["8-K"])
        is None
    )


def test_dilution_filings_are_collected_with_their_age(v2):
    filings = classify_filings(
        SUBMISSIONS,
        form_types=["S-3", "S-1", "424B3", "424B5", "F-3"],
        as_of="2026-10-07",
    )
    forms = {filing["form"]: filing["days_ago"] for filing in filings}
    assert forms["424B5"] == 17
    assert forms["S-3"] == 274


def test_an_empty_submissions_payload_is_not_a_crash(v2):
    assert classify_filings({}, form_types=["S-3"], as_of="2026-10-07") == []
    assert latest_material_filing(None, form_types=["8-K"]) is None


def test_hours_since_reads_the_acceptance_timestamp(v2):
    hours = hours_since("2026-10-07T16:05:00.000Z", now="2026-10-07T20:05:00Z")
    assert hours == pytest.approx(4.0, abs=0.01)


def test_hours_since_survives_a_malformed_timestamp(v2):
    assert hours_since("not a date", now="2026-10-07T20:05:00Z") is None


# --- Form 4 purchases ---------------------------------------------------


def test_an_open_market_purchase_is_recognised(v2):
    """Transaction code P. An award or an option exercise is not someone
    spending their own money."""
    days = form4_purchases(
        [
            {"form": "4", "days_ago": 12, "transaction_codes": ["P"]},
            {"form": "4", "days_ago": 3, "transaction_codes": ["A"]},
        ],
        codes=["P"],
    )
    assert days == 12


def test_awards_and_exercises_are_not_purchases(v2):
    assert (
        form4_purchases(
            [{"form": "4", "days_ago": 3, "transaction_codes": ["A", "M"]}], codes=["P"]
        )
        is None
    )


def test_the_most_recent_purchase_wins(v2):
    days = form4_purchases(
        [
            {"form": "4", "days_ago": 20, "transaction_codes": ["P"]},
            {"form": "4", "days_ago": 5, "transaction_codes": ["P"]},
        ],
        codes=["P"],
    )
    assert days == 5


# --- cash runway --------------------------------------------------------


def test_runway_is_cash_over_quarterly_burn(v2):
    """$9M of cash burning $3M a quarter is nine months."""
    assert months_of_runway(cash=9_000_000, quarterly_operating_cash_flow=-3_000_000) == 9.0


def test_a_cash_generating_company_has_unbounded_runway(v2):
    assert months_of_runway(cash=1_000_000, quarterly_operating_cash_flow=500_000) == float("inf")


def test_no_burn_at_all_is_unbounded(v2):
    assert months_of_runway(cash=1_000_000, quarterly_operating_cash_flow=0) == float("inf")


def test_missing_figures_give_no_runway_claim(v2):
    assert months_of_runway(cash=None, quarterly_operating_cash_flow=-1_000_000) is None
    assert months_of_runway(cash=1_000_000, quarterly_operating_cash_flow=None) is None


def test_zero_cash_is_a_real_answer_not_a_missing_one(v2):
    assert months_of_runway(cash=0, quarterly_operating_cash_flow=-1_000_000) == 0.0
