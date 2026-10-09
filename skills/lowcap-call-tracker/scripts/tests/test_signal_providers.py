"""The measurement side of the signals layer: the maths, not the network.

Every provider takes already-fetched rows so the arithmetic is testable
offline, and every one of them answers None when its input is missing. These
tests are the contract the network wrappers have to keep.
"""

import pytest
from signal_providers import (
    borrow_fee_from_iborrowdesk,
    count_halts,
    gather_signal_data,
    peer_count_from_rows,
    premarket_stats,
    range_percentile,
    reverse_split_age,
    session_vwap,
)

# --- VWAP ---------------------------------------------------------------


def bar(high, low, close, volume, *, when="2026-10-07 10:00"):
    return {"datetime": when, "high": high, "low": low, "close": close, "volume": volume}


def test_vwap_is_volume_weighted_not_an_average_of_closes():
    """One big print near the low has to drag VWAP down to it."""
    bars = [
        bar(10.0, 10.0, 10.0, 100),
        bar(12.0, 12.0, 12.0, 100),
        bar(8.0, 8.0, 8.0, 10_000),
    ]
    assert session_vwap(bars) == pytest.approx(8.06, abs=0.01)


def test_vwap_uses_the_typical_price_of_each_bar():
    bars = [bar(11.0, 9.0, 10.0, 1000)]
    assert session_vwap(bars) == pytest.approx(10.0, abs=0.001)


def test_zero_volume_bars_are_ignored():
    bars = [bar(10.0, 10.0, 10.0, 0), bar(20.0, 20.0, 20.0, 500)]
    assert session_vwap(bars) == pytest.approx(20.0, abs=0.001)


def test_no_bars_gives_no_vwap():
    assert session_vwap([]) is None
    assert session_vwap(None) is None


def test_a_session_with_no_volume_at_all_gives_no_vwap():
    assert session_vwap([bar(10.0, 10.0, 10.0, 0)]) is None


# --- premarket ----------------------------------------------------------


def test_the_premarket_gap_is_measured_from_the_prior_close():
    stats = premarket_stats(
        [
            {"datetime": "2026-10-07 07:30", "close": 4.40, "volume": 150_000},
            {"datetime": "2026-10-07 08:45", "close": 4.60, "volume": 150_000},
        ],
        prior_close=4.00,
        avg_volume=1_000_000,
    )
    assert stats["premarket_gap_pct"] == pytest.approx(15.0, abs=0.01)
    assert stats["premarket_volume_pct_of_adv"] == pytest.approx(30.0, abs=0.01)


def test_the_last_premarket_print_sets_the_gap():
    stats = premarket_stats(
        [
            {"datetime": "2026-10-07 07:30", "close": 5.00, "volume": 10},
            {"datetime": "2026-10-07 09:15", "close": 4.20, "volume": 10},
        ],
        prior_close=4.00,
        avg_volume=1_000,
    )
    assert stats["premarket_gap_pct"] == pytest.approx(5.0, abs=0.01)


def test_regular_session_bars_are_not_premarket():
    stats = premarket_stats(
        [{"datetime": "2026-10-07 10:30", "close": 4.40, "volume": 500_000}],
        prior_close=4.00,
        avg_volume=1_000_000,
    )
    assert stats["premarket_gap_pct"] is None


def test_no_prior_close_means_no_gap_claim():
    stats = premarket_stats(
        [{"datetime": "2026-10-07 08:00", "close": 4.40, "volume": 10}],
        prior_close=None,
        avg_volume=1_000_000,
    )
    assert stats["premarket_gap_pct"] is None


def test_no_average_volume_means_no_volume_share():
    stats = premarket_stats(
        [{"datetime": "2026-10-07 08:00", "close": 4.40, "volume": 10}],
        prior_close=4.00,
        avg_volume=None,
    )
    assert stats["premarket_gap_pct"] == pytest.approx(10.0, abs=0.01)
    assert stats["premarket_volume_pct_of_adv"] is None


# --- volatility contraction --------------------------------------------


def daily(high, low, close=None):
    return {"high": high, "low": low, "close": close if close is not None else (high + low) / 2}


def test_a_tight_recent_range_lands_in_a_low_percentile():
    """Fifty wide sessions then ten tight ones: the tight window is the
    narrowest range in the lookback."""
    bars = [daily(12.0, 8.0) for _ in range(50)] + [daily(10.1, 9.9) for _ in range(10)]
    percentile = range_percentile(bars, window=10, lookback=60)
    assert percentile is not None
    assert percentile <= 5.0


def test_a_wide_recent_range_lands_high():
    bars = [daily(10.1, 9.9) for _ in range(50)] + [daily(14.0, 6.0) for _ in range(10)]
    assert range_percentile(bars, window=10, lookback=60) >= 90.0


def test_too_little_history_gives_no_percentile():
    assert range_percentile([daily(10.0, 9.0) for _ in range(8)], window=10, lookback=60) is None


def test_no_bars_gives_no_percentile():
    assert range_percentile([], window=10, lookback=60) is None
    assert range_percentile(None, window=10, lookback=60) is None


def test_a_flat_history_is_not_a_division_by_zero():
    bars = [daily(10.0, 10.0) for _ in range(60)]
    assert range_percentile(bars, window=10, lookback=60) is not None


# --- borrow fee ---------------------------------------------------------


def test_the_latest_borrow_fee_is_read():
    payload = {
        "daily": [
            {"date": "2026-10-06", "fee": 18.5, "available": 20000},
            {"date": "2026-10-07", "fee": 42.25, "available": 0},
        ]
    }
    assert borrow_fee_from_iborrowdesk(payload) == 42.25


def test_an_empty_borrow_payload_is_none():
    assert borrow_fee_from_iborrowdesk({"daily": []}) is None
    assert borrow_fee_from_iborrowdesk({}) is None
    assert borrow_fee_from_iborrowdesk(None) is None


def test_a_borrow_payload_without_a_fee_is_none():
    assert borrow_fee_from_iborrowdesk({"daily": [{"date": "2026-10-07"}]}) is None


# --- halts --------------------------------------------------------------


HALT_XML = """<?xml version="1.0"?><rss><channel>
<item><ndaq:IssueSymbol xmlns:ndaq="x">EXPL</ndaq:IssueSymbol><ndaq:HaltDate xmlns:ndaq="x">10/07/2026</ndaq:HaltDate></item>
<item><ndaq:IssueSymbol xmlns:ndaq="x">EXPL</ndaq:IssueSymbol><ndaq:HaltDate xmlns:ndaq="x">10/07/2026</ndaq:HaltDate></item>
<item><ndaq:IssueSymbol xmlns:ndaq="x">EXPL</ndaq:IssueSymbol><ndaq:HaltDate xmlns:ndaq="x">10/07/2026</ndaq:HaltDate></item>
<item><ndaq:IssueSymbol xmlns:ndaq="x">OTHR</ndaq:IssueSymbol><ndaq:HaltDate xmlns:ndaq="x">10/07/2026</ndaq:HaltDate></item>
<item><ndaq:IssueSymbol xmlns:ndaq="x">EXPL</ndaq:IssueSymbol><ndaq:HaltDate xmlns:ndaq="x">10/06/2026</ndaq:HaltDate></item>
</channel></rss>"""


def test_halts_are_counted_per_symbol_for_today_only():
    assert count_halts(HALT_XML, "EXPL", as_of="2026-10-07") == 3
    assert count_halts(HALT_XML, "OTHR", as_of="2026-10-07") == 1


def test_a_symbol_with_no_halts_counts_zero_not_unknown():
    """The feed was read, so "no halts" is a fact about this symbol."""
    assert count_halts(HALT_XML, "CALM", as_of="2026-10-07") == 0


def test_an_unreadable_halt_feed_is_unknown():
    assert count_halts(None, "EXPL", as_of="2026-10-07") is None
    assert count_halts("<not xml", "EXPL", as_of="2026-10-07") is None


# --- reverse split ------------------------------------------------------


def test_a_reverse_split_is_a_ratio_below_one():
    splits = {"2026-08-20": 0.1, "2024-01-05": 2.0}
    assert reverse_split_age(splits, as_of="2026-10-07") == 48


def test_a_forward_split_is_not_a_reverse_split():
    assert reverse_split_age({"2026-09-01": 3.0}, as_of="2026-10-07") is None


def test_the_most_recent_reverse_split_is_reported():
    splits = {"2020-01-01": 0.05, "2026-09-07": 0.2}
    assert reverse_split_age(splits, as_of="2026-10-07") == 30


def test_no_split_history_is_unknown_not_clean():
    """yfinance returning nothing is not proof the company never split."""
    assert reverse_split_age(None, as_of="2026-10-07") is None


def test_an_empty_split_history_is_clean():
    assert reverse_split_age({}, as_of="2026-10-07") is None


# --- sector sympathy ----------------------------------------------------


MOVERS = [
    {"ticker": "AAA", "industry": "Biotechnology", "change_pct": 22.0},
    {"ticker": "BBB", "industry": "Biotechnology", "change_pct": 14.0},
    {"ticker": "CCC", "industry": "Biotechnology", "change_pct": 4.0},
    {"ticker": "DDD", "industry": "Semiconductors", "change_pct": 30.0},
    {"ticker": "EXPL", "industry": "Biotechnology", "change_pct": 18.0},
]


def test_peers_are_counted_in_the_same_industry_above_the_threshold():
    assert (
        peer_count_from_rows(MOVERS, ticker="EXPL", industry="Biotechnology", min_change=10.0) == 2
    )


def test_the_name_itself_is_never_its_own_peer():
    """Counting yourself turns every lone runner into a sector theme. AAA is
    up 22%, and its peers are BBB and EXPL — three qualifying rows in the
    industry, two of them peers."""
    assert (
        peer_count_from_rows(MOVERS, ticker="AAA", industry="Biotechnology", min_change=10.0) == 2
    )
    assert (
        peer_count_from_rows(
            [{"ticker": "LONE", "industry": "Biotechnology", "change_pct": 40.0}],
            ticker="LONE",
            industry="Biotechnology",
            min_change=10.0,
        )
        == 0
    )


def test_a_different_industry_has_its_own_count():
    assert (
        peer_count_from_rows(MOVERS, ticker="EXPL", industry="Semiconductors", min_change=10.0) == 1
    )


def test_no_industry_on_the_row_means_no_peer_claim():
    assert peer_count_from_rows(MOVERS, ticker="EXPL", industry=None, min_change=10.0) is None


def test_no_mover_scan_means_no_peer_claim():
    assert (
        peer_count_from_rows(None, ticker="EXPL", industry="Biotechnology", min_change=10.0) is None
    )


def test_an_empty_mover_scan_is_a_real_zero():
    assert peer_count_from_rows([], ticker="EXPL", industry="Biotechnology", min_change=10.0) == 0


# --- the gatherer -------------------------------------------------------


def test_gathering_offline_returns_an_all_na_sheet(config):
    """--offline must not reach for a single source, and must still produce a
    sheet the scorer can read."""
    config["screener"]["screener_version"] = "v2"
    data = gather_signal_data({"ticker": "EXPL", "price": 4.0}, config, offline=True)
    assert data["offline"] is True
    assert data["vwap"] is None
    assert data["dilution_filings"] is None
    assert data["notes"]


def test_gathering_for_a_v1_hit_does_nothing(config):
    data = gather_signal_data({"ticker": "EXPL", "screener_version": "v1"}, config)
    assert data == {}


def test_a_screener_headline_survives_an_offline_run(config):
    """The headline is on the row already: refusing to read it offline would
    throw away the one catalyst source that needs no network."""
    config["screener"]["screener_version"] = "v2"
    data = gather_signal_data(
        {"ticker": "EXPL", "price": 4.0, "catalyst_headline": "FDA clears lead program"},
        config,
        offline=True,
    )
    assert data["news_hours_ago"] == 12.0


def test_an_offline_run_with_no_headline_claims_no_catalyst_data(config):
    config["screener"]["screener_version"] = "v2"
    data = gather_signal_data({"ticker": "EXPL", "price": 4.0}, config, offline=True)
    assert data["news_hours_ago"] is None
    assert data["catalyst_found"] is None


# --- bar timestamps must be read in market time -------------------------


def test_a_utc_timestamp_is_classified_in_market_time():
    """yfinance returns ET from Ticker.history and UTC from download(). A
    13:00 UTC bar is 09:00 ET — pre-market — and reading the hour off the
    string would file it as the regular session."""
    from signal_providers import bar_minute_et

    assert bar_minute_et("2026-10-09 13:00:00+00:00") == 9 * 60
    assert bar_minute_et("2026-10-09 09:25:00-04:00") == 9 * 60 + 25
    assert bar_minute_et("2026-10-09 14:30:00+00:00") == 10 * 60 + 30


def test_a_naive_timestamp_is_read_as_market_time():
    from signal_providers import bar_minute_et

    assert bar_minute_et("2026-10-09 07:30:00") == 7 * 60 + 30


def test_an_unreadable_timestamp_has_no_minute():
    from signal_providers import bar_minute_et

    assert bar_minute_et("nonsense") is None
    assert bar_minute_et(None) is None


def test_premarket_bars_are_selected_in_market_time():
    """The same session, labelled in UTC, must still read as pre-market."""
    stats = premarket_stats(
        [
            {"datetime": "2026-10-09 11:30:00+00:00", "close": 4.40, "volume": 100},
            {"datetime": "2026-10-09 13:15:00+00:00", "close": 4.60, "volume": 100},
        ],
        prior_close=4.00,
        avg_volume=1_000,
    )
    assert stats["premarket_gap_pct"] == pytest.approx(15.0, abs=0.01)


def test_a_utc_labelled_regular_bar_is_not_premarket():
    stats = premarket_stats(
        [{"datetime": "2026-10-09 15:00:00+00:00", "close": 4.40, "volume": 100}],
        prior_close=4.00,
        avg_volume=1_000,
    )
    assert stats["premarket_gap_pct"] is None


# --- volume the provider does not report -------------------------------


def test_zero_premarket_volume_is_unknown_not_zero():
    """Measured 2026-10-09: yfinance reports 0.0 volume on EVERY pre/post bar
    at every interval, so a summed zero means the provider does not publish
    pre-market volume — not that nobody traded. Reporting 0% of ADV refuses
    exactly the names a gap screen exists to find.
    """
    stats = premarket_stats(
        [
            {"datetime": "2026-10-09 07:30:00", "close": 4.40, "volume": 0.0},
            {"datetime": "2026-10-09 08:45:00", "close": 4.60, "volume": 0.0},
        ],
        prior_close=4.00,
        avg_volume=1_000_000,
    )
    assert stats["premarket_gap_pct"] == pytest.approx(15.0, abs=0.01)
    assert stats["premarket_volume_pct_of_adv"] is None


def test_real_premarket_volume_is_still_measured():
    """If the provider ever starts reporting it, nothing here changes."""
    stats = premarket_stats(
        [{"datetime": "2026-10-09 07:30:00", "close": 4.40, "volume": 250_000}],
        prior_close=4.00,
        avg_volume=1_000_000,
    )
    assert stats["premarket_volume_pct_of_adv"] == pytest.approx(25.0, abs=0.01)
