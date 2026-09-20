"""Variant filter codes, URL building and screener-row normalization."""

import json

import pytest
from fetch_screener import (
    FetchError,
    load_fixture,
    merge_rows,
    normalize_row,
    parse_export_csv,
    parse_number,
    parse_screener_html,
    screen_all,
    screen_variant,
)
from screener_variants import (
    VariantError,
    build_variant_urls,
    describe_variants,
    exchange_filter_sets,
    validate_token,
    variant_filters,
    variant_views,
)

# The filter codes the workflow documents. Kept explicit so a config edit that
# silently drops a requirement fails the suite.
SQUEEZE_EXPECTED = {
    "cap_smallunder",
    "sh_price_1to20",
    "sh_avgvol_o500",
    "sh_relvol_o2",
    "ta_perf_dup",
    "ta_sma20_pa",
    "ta_sma50_pa",
    "ind_stocksonly",
    "geo_usa",
    "sh_float_u20",
    "sh_short_o15",
}
MOMENTUM_EXPECTED = {
    "cap_smallunder",
    "sh_price_1to20",
    "sh_avgvol_o500",
    "sh_relvol_o3",
    "ta_perf_dup",
    "ta_sma20_pa",
    "ta_sma50_pa",
    "ta_highlow52w_nh",
    "ind_stocksonly",
    "geo_usa",
    "sh_float_u20",
}
ETF_EXPECTED = {
    "ind_exchangetradedfund",
    "sh_price_1to20",
    "sh_avgvol_o500",
    "sh_relvol_o2",
    "ta_perf_dup",
    "ta_sma20_pa",
    "ta_sma50_pa",
    "ta_highlow52w_nh",
}


def test_squeeze_filters_match_the_specification(config):
    assert set(variant_filters(config, "squeeze")) == SQUEEZE_EXPECTED


def test_momentum_breakout_requires_new_high_and_relvol_3(config):
    filters = set(variant_filters(config, "momentum_breakout"))
    assert filters == MOMENTUM_EXPECTED
    assert "sh_relvol_o3" in filters and "sh_relvol_o2" not in filters


def test_etf_variant_omits_float_short_float_and_market_cap(config):
    """FinViz publishes no float / short-float for ETFs, so those filters would
    drop every ETF row; market cap is likewise absent for many funds."""
    filters = set(variant_filters(config, "etf_momentum"))
    assert filters == ETF_EXPECTED
    assert not [token for token in filters if token.startswith(("sh_float", "sh_short", "cap_"))]
    assert "ownership" not in variant_views(config, "etf_momentum")


def test_short_float_floor_is_available_as_an_opt_in(config):
    config["screener"]["variants"]["momentum_breakout"]["enable_optional"] = ["short_float_filter"]
    assert "sh_short_o15" in variant_filters(config, "momentum_breakout")


def test_enable_optional_rejects_an_unknown_key(config):
    config["screener"]["variants"]["squeeze"]["enable_optional"] = ["nope"]
    with pytest.raises(VariantError):
        variant_filters(config, "squeeze")


def test_ownership_view_is_requested_for_stock_variants(config):
    for variant in ("squeeze", "momentum_breakout"):
        assert "ownership" in variant_views(config, variant)


def test_urls_are_built_per_view(config):
    urls = build_variant_urls(config, "squeeze")
    assert {entry["view"] for entry in urls} == {
        "overview",
        "ownership",
        "performance",
        "technical",
    }
    for entry in urls:
        assert entry["url"].startswith("https://finviz.com/screener.ashx?v=")
        assert "sh_short_o15" in entry["url"]


def test_exchange_mode_explicit_uses_multi_select(config):
    config["screener"]["exchange_mode"] = "explicit"
    assert exchange_filter_sets(config) == [["exch_amex|nasd|nyse"]]


def test_exchange_mode_per_exchange_produces_one_pass_each(config):
    config["screener"]["exchange_mode"] = "per_exchange"
    assert exchange_filter_sets(config) == [["exch_amex"], ["exch_nasd"], ["exch_nyse"]]


def test_exchange_mode_universe_adds_no_token(config):
    config["screener"]["exchange_mode"] = "universe"
    assert exchange_filter_sets(config) == [[]]


@pytest.mark.parametrize(
    "token", ["ta_sma20_pa&x=1", "cap_small ", "CAP_SMALL", "a,b", "sh_price_1to20;drop"]
)
def test_filter_tokens_reject_injection(token):
    if token.strip() != token and token.strip():
        assert validate_token(token) == token.strip()
        return
    with pytest.raises(VariantError):
        validate_token(token)


def test_multi_select_pipe_is_allowed():
    assert validate_token("exch_amex|nasd|nyse") == "exch_amex|nasd|nyse"


def test_describe_variants_reports_all_three(config):
    described = describe_variants(config)
    assert [entry["variant"] for entry in described] == [
        "squeeze",
        "momentum_breakout",
        "etf_momentum",
    ]
    assert [entry["asset_type"] for entry in described] == ["stock", "stock", "etf"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.25B", 1_250_000_000.0),
        ("12.30M", 12_300_000.0),
        ("450K", 450_000.0),
        ("5.10%", 5.1),
        ("-3.20%", -3.2),
        ("1,234,567", 1_234_567.0),
        ("-", None),
        ("", None),
        ("N/A", None),
        (None, None),
        (4.5, 4.5),
    ],
)
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_normalize_row_maps_finviz_headers():
    row = normalize_row(
        {
            "Ticker": "abcd",
            "Company": "Abcd Inc",
            "Float": "12.30M",
            "Float Short": "22.50%",
            "Rel Volume": "3.40",
            "Avg Volume": "1.2M",
            "SMA20": "18.00%",
            "52W High": "-3.00%",
            "Price": "4.55",
            "Change": "22.40%",
        }
    )
    assert row["ticker"] == "ABCD"
    assert row["float_shares"] == 12_300_000.0
    assert row["short_float_pct"] == 22.5
    assert row["rel_volume"] == 3.4
    assert row["sma20_pct"] == 18.0
    assert row["high52w_pct"] == -3.0
    assert row["change_pct"] == 22.4


def test_parse_export_csv():
    csv_text = "Ticker,Company,Price,Change\nAAA,Alpha Inc,3.10,15.00%\nBBB,Beta Inc,7.20,4.00%\n"
    rows = parse_export_csv(csv_text)
    assert [row["ticker"] for row in rows] == ["AAA", "BBB"]
    assert rows[0]["price"] == 3.10


def test_parse_screener_html():
    html = """
    <html><body>
    <table class="other"><tr><th>Nope</th></tr><tr><td>x</td></tr></table>
    <table>
      <tr><th>Ticker</th><th>Price</th><th>Change</th><th>Rel Volume</th></tr>
      <tr><td>AAA</td><td>3.10</td><td>15.00%</td><td>4.20</td></tr>
      <tr><td>BBB</td><td>7.20</td><td>4.00%</td><td>2.10</td></tr>
    </table>
    </body></html>
    """
    rows = parse_screener_html(html)
    assert [row["ticker"] for row in rows] == ["AAA", "BBB"]
    assert rows[0]["rel_volume"] == 4.2


def test_parse_screener_html_without_ticker_table_returns_empty():
    assert parse_screener_html("<html><table><tr><th>Nope</th></tr></table></html>") == []


def test_merge_rows_fills_missing_fields_only():
    merged = merge_rows(
        [
            [{"ticker": "AAA", "price": 3.1, "rel_volume": None}],
            [{"ticker": "AAA", "rel_volume": 4.2, "price": 9.9}],
            [{"ticker": "BBB", "price": 1.0}],
        ]
    )
    assert merged["AAA"]["price"] == 3.1  # first view wins
    assert merged["AAA"]["rel_volume"] == 4.2  # later view fills the gap
    assert set(merged) == {"AAA", "BBB"}


def test_fixture_mode_tags_variant_and_asset_type(config, tmp_path):
    from conftest import FIXTURE_HITS

    hits = screen_variant(config, "etf_momentum", fixture=str(FIXTURE_HITS))
    assert [hit["ticker"] for hit in hits] == ["URAX"]
    assert hits[0]["asset_type"] == "etf"
    assert hits[0]["screen_mode"] == "fixture"


def test_screen_all_covers_every_variant_from_the_fixture(config):
    from conftest import FIXTURE_HITS

    hits = screen_all(config, fixture=str(FIXTURE_HITS))
    assert {hit["ticker"] for hit in hits} == {"SQZX", "PMPX", "URAX"}
    assert {hit["variant"] for hit in hits} == {"squeeze", "momentum_breakout", "etf_momentum"}


def test_rows_from_disallowed_exchanges_are_dropped(config, tmp_path):
    fixture = tmp_path / "hits.json"
    fixture.write_text(
        json.dumps(
            [
                {"ticker": "OTCX", "variant": "squeeze", "price": 2.0, "exchange": "OTC"},
                {"ticker": "GOOD", "variant": "squeeze", "price": 2.0, "exchange": "NASD"},
            ]
        ),
        encoding="utf-8",
    )
    hits = screen_variant(config, "squeeze", fixture=str(fixture))
    assert [hit["ticker"] for hit in hits] == ["GOOD"]


def test_fixture_must_be_a_list(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"rows": 1}), encoding="utf-8")
    with pytest.raises(FetchError):
        load_fixture(str(bad))


def test_public_parsing_without_beautifulsoup4_explains_the_options(monkeypatch):
    """beautifulsoup4 is optional: the public HTML path degrades with guidance."""
    import fetch_screener

    monkeypatch.setattr(fetch_screener, "HAS_BS4", False)
    with pytest.raises(FetchError) as excinfo:
        fetch_screener.parse_screener_html("<html><table><tr><th>Ticker</th></tr></table></html>")
    message = str(excinfo.value)
    assert "beautifulsoup4" in message
    assert "FINVIZ_API_KEY" in message and "--fixture" in message


def test_elite_and_fixture_paths_do_not_need_beautifulsoup4(config, monkeypatch):
    import fetch_screener

    from conftest import FIXTURE_HITS

    monkeypatch.setattr(fetch_screener, "HAS_BS4", False)
    assert fetch_screener.parse_export_csv("Ticker,Price\nAAA,3.10\n")[0]["ticker"] == "AAA"
    assert screen_variant(config, "squeeze", fixture=str(FIXTURE_HITS))
