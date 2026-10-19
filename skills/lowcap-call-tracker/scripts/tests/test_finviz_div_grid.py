"""FinViz replaced its results <table> with a div grid. Parse that too.

Measured 2026-10-19. The public screener page still loads — 358KB, the right
title, our filters echoed back — and contains ZERO `<table>` elements. The
grid is now `div.fv-table_row` with `div.fv-table_cell` children and
`div.fv-table_header-cell` headers.

The parser looked only for tables, so it returned no rows, and the cycle
reported "hits=0" as though the market were quiet. A structural screen (small
cap, $1-20, avg volume over 300K, US stocks) matches thousands of names, so
zero was never plausible — but nothing in the output said so. The last
successful screen was 2026-10-16.

Two changes are tested here:

* the div grid parses, with the ticker taken from `data-row-key` (the cell
  text still doubles the first letter: "TTCRT" for TCRT);
* a page with no recognisable grid AT ALL now raises instead of returning [],
  because a silent zero is indistinguishable from a quiet market. A grid with
  a header and no rows still returns [] — that is a real empty result.
"""

import pytest
from fetch_screener import FetchError, parse_screener_html

# Trimmed from the live page, structure preserved: header cells carry a long
# and a short label, the ticker cell doubles its first letter, and the row's
# real symbol is in data-row-key.
DIV_GRID = """
<div class="fv-table">
  <div class="fv-table_header-row" role="row">
    <div class="fv-table_header-cell"><span class="fv-table_header-label">No.</span></div>
    <div class="fv-table_header-cell"><span class="fv-table_header-label">Ticker</span></div>
    <div class="fv-table_header-cell"><span class="fv-table_header-label">Company</span></div>
    <div class="fv-table_header-cell"><span class="fv-table_header-label">Sector</span></div>
    <div class="fv-table_header-cell">
      <span class="fv-table_header-label">Market Cap</span>
      <span class="fv-table_header-label-short">Mkt Cap</span>
    </div>
    <div class="fv-table_header-cell"><span class="fv-table_header-label">Price</span></div>
    <div class="fv-table_header-cell">
      <span class="fv-table_header-label">Change %</span>
      <span class="fv-table_header-label-short">Chg %</span>
    </div>
    <div class="fv-table_header-cell">
      <span class="fv-table_header-label">Volume</span>
      <span class="fv-table_header-label-short">Vol</span>
    </div>
  </div>
  <div class="fv-table_row" data-row-key="XLAB" role="row" data-row-index="0">
    <div class="fv-table_cell">1</div>
    <div class="fv-table_cell"><a class="fv-table_link" href="/quote?t=XLAB&amp;b=1">
      <span>X</span><span>XLAB</span></a></div>
    <div class="fv-table_cell">Exascale Labs Holdings Inc</div>
    <div class="fv-table_cell">Technology</div>
    <div class="fv-table_cell">87.43M</div>
    <div class="fv-table_cell">2.60</div>
    <div class="fv-table_cell">10.43%</div>
    <div class="fv-table_cell">55,293,202</div>
  </div>
  <div class="fv-table_row" data-row-key="TCRT" role="row" data-row-index="1">
    <div class="fv-table_cell">2</div>
    <div class="fv-table_cell"><a class="fv-table_link" href="/quote?t=TCRT&amp;b=1">
      <span>T</span><span>TCRT</span></a></div>
    <div class="fv-table_cell">Alaunos Therapeutics Inc</div>
    <div class="fv-table_cell">Healthcare</div>
    <div class="fv-table_cell">8.66M</div>
    <div class="fv-table_cell">2.95</div>
    <div class="fv-table_cell">12.36%</div>
    <div class="fv-table_cell">33,796,821</div>
  </div>
</div>
"""

EMPTY_GRID = """
<div class="fv-table">
  <div class="fv-table_header-row" role="row">
    <div class="fv-table_header-cell"><span class="fv-table_header-label">No.</span></div>
    <div class="fv-table_header-cell"><span class="fv-table_header-label">Ticker</span></div>
    <div class="fv-table_header-cell"><span class="fv-table_header-label">Price</span></div>
  </div>
</div>
"""

TABLE_GRID = """
<table class="screener_table">
  <tr><td>No.</td><td>Ticker</td><td>Company</td><td>Price</td><td>Change</td></tr>
  <tr><td>1</td><td data-boxover-ticker="AAPL">AAAPL</td><td>Apple Inc</td>
      <td>190.00</td><td>1.20%</td></tr>
</table>
"""


def test_the_div_grid_parses():
    rows = parse_screener_html(DIV_GRID)
    assert [row["ticker"] for row in rows] == ["XLAB", "TCRT"]


def test_the_ticker_comes_from_the_row_key_not_the_doubled_text():
    """The cell renders a logo letter then the symbol, so its text is "TTCRT"."""
    rows = parse_screener_html(DIV_GRID)
    assert rows[1]["ticker"] == "TCRT"


def test_the_long_header_label_is_the_one_used():
    """ "Market CapMkt Cap" matches nothing in COLUMN_MAP; "Market Cap" does."""
    rows = parse_screener_html(DIV_GRID)
    assert rows[0]["market_cap"] == pytest.approx(87_430_000)
    assert rows[0]["change_pct"] == pytest.approx(10.43)
    assert rows[0]["volume"] == pytest.approx(55_293_202)


def test_the_other_fields_still_normalize():
    row = parse_screener_html(DIV_GRID)[0]
    assert row["company"] == "Exascale Labs Holdings Inc"
    assert row["sector"] == "Technology"
    assert row["price"] == pytest.approx(2.60)


def test_a_grid_with_a_header_and_no_rows_is_a_real_empty_result():
    assert parse_screener_html(EMPTY_GRID) == []


def test_a_page_with_no_grid_at_all_raises():
    """The failure mode this whole file exists for: 358KB of valid screener
    page, no recognisable grid, and a cycle that reported a quiet market."""
    with pytest.raises(FetchError, match="could not find"):
        parse_screener_html("<html><body><div>nothing here</div></body></html>")


def test_the_old_table_markup_still_parses():
    """Elite export aside, FinViz may serve either; neither path may break."""
    rows = parse_screener_html(TABLE_GRID)
    assert [row["ticker"] for row in rows] == ["AAPL"]
