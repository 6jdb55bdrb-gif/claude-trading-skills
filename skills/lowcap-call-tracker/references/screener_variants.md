# Screener variants and filter codes

Three variants over the US low-cap universe. Codes are FinViz screener filter
tokens; the full catalogue lives in
`skills/finviz-screener/references/finviz_screener_filters.md`, and URLs are
built by that skill's `build_url` so both skills emit identical URLs.

## FinViz markup: the results grid is a div grid, not a table

Measured 2026-10-19. The public screener page replaced
`<table class="screener_table">` with a div grid and now contains **zero
`<table>` elements**:

| element | class | carries |
|---|---|---|
| header cell | `fv-table_header-cell` | a long label (`fv-table_header-label`) and sometimes a short one (`...-label-short`), so the cell's own text runs them together — "Market CapMkt Cap", "VolumeVol" — and matches nothing in `COLUMN_MAP`. Read the long label. |
| row | `fv-table_row` | `data-row-key="TCRT"`, the authoritative symbol |
| cell | `fv-table_cell` | the values, in header order |
| ticker link | `fv-table_link` | `/quote?t=TCRT&b=1` — note `/quote`, not the old `/quote.ashx` |

The ticker CELL still doubles the first letter ("TTCRT" for TCRT) because it
renders a logo letter and then the symbol, so the symbol comes from
`data-row-key`, with the link's `?t=` as a fallback.

**How this was found, and the lesson.** The 2026-10-19 10:47 ET cycle reported
`hits=0` with no error. A structural screen — small cap, $1-20, average volume
over 300K, US stocks — matches thousands of names, so zero was never plausible,
but nothing in the output said so: the parser looked for tables, found none,
and returned `[]`. The page itself was fine (358KB, correct title, our filters
echoed back in it).

`parse_screener_html` now **raises `FetchError`** when it can find no grid of
either shape. A grid that is present with no rows still returns `[]`, because
that is a real empty result — `momentum_breakout` was legitimately empty the
same morning ("0 Total" on the page). The distinction is the whole point: an
unparsable page must never again read as a quiet market.

This is the same failure class as the filter-token lesson below — FinViz fails
silently, so every layer that reads it has to tell "nothing matched" apart from
"I could not read the answer".

## Shared base (all variants)

| Requirement | Filter code | Note |
|---|---|---|
| Price $1–$20 | `sh_price_1to20` | custom range; FinViz has no `1to20` preset button, the range syntax works |
| Average volume over 500K | `sh_avgvol_o500` | `_o500` is in thousands |
| Up today | `ta_perf_dup` | Performance → Today Up |
| Above the SMA20 | `ta_sma20_pa` | |
| Above the SMA50 | `ta_sma50_pa` | |

## Variant 1 — `squeeze` (stocks)

High short float on a small float: the classic squeeze set-up.

| Requirement | Filter code |
|---|---|
| Market cap under $2B (small + micro + nano) | `cap_smallunder` |
| Price $1–$20 | `sh_price_1to20` |
| Average volume over 500K | `sh_avgvol_o500` |
| Relative volume over 2 | `sh_relvol_o2` |
| Up today | `ta_perf_dup` |
| Above SMA20 | `ta_sma20_pa` |
| Above SMA50 | `ta_sma50_pa` |
| Stocks only (excludes funds and ETFs) | `ind_stocksonly` |
| US companies | `geo_usa` |
| **Float under 20M shares** | `sh_float_u20` |
| **Short float over 15%** | `sh_short_o15` |

Views fetched and merged: `overview` (111), `ownership` (131), `performance`
(141), `technical` (171). Sort: `-relativevolume`.

Tightening options: `sh_short_o20` / `sh_short_o25` for heavier short interest,
`sh_float_u10` for a tighter float, `sh_relvol_o3` for a stronger surge.

## Variant 2 — `momentum_breakout` (stocks)

New 52-week high on a volume surge.

| Requirement | Filter code |
|---|---|
| Market cap under $2B | `cap_smallunder` |
| Price $1–$20 | `sh_price_1to20` |
| Average volume over 500K | `sh_avgvol_o500` |
| **Relative volume over 3** | `sh_relvol_o3` |
| Up today | `ta_perf_dup` |
| Above SMA20 | `ta_sma20_pa` |
| Above SMA50 | `ta_sma50_pa` |
| **New 52-week high** | `ta_highlow52w_nh` |
| Stocks only | `ind_stocksonly` |
| US companies | `geo_usa` |
| Float under 20M shares | `sh_float_u20` |
| *Short float over 15% (opt-in)* | `sh_short_o15` |

**Why short float is opt-in here.** The global specification asks for short float
over 15% on stocks, but a stock printing a fresh 52-week high on 3x volume is
frequently *not* heavily shorted — requiring both empties the variant on most
days. The code is configured but disabled; enable it with:

```yaml
screener:
  variants:
    momentum_breakout:
      enable_optional: [short_float_filter]
```

The `squeeze` variant carries the >15% floor unconditionally, so the requirement
is always represented in the run.

## Variant 3 — `etf_momentum` (ETFs only)

| Requirement | Filter code |
|---|---|
| ETFs only | `ind_exchangetradedfund` |
| Price $1–$20 | `sh_price_1to20` |
| Average volume over 500K | `sh_avgvol_o500` |
| Relative volume over 2 | `sh_relvol_o2` |
| Up today | `ta_perf_dup` |
| Above SMA20 | `ta_sma20_pa` |
| Above SMA50 | `ta_sma50_pa` |
| New 52-week high | `ta_highlow52w_nh` |

**Deliberately absent:** `sh_float_u20`, `sh_short_o15` and every `cap_*` token.
FinViz publishes no float or short-float figures for ETFs and reports market cap
as `-` for most funds, so any of those filters removes every ETF row. The
ownership view (131) is not fetched for this variant for the same reason, and the
Skeptic is instructed never to treat the missing fields as a risk flag — it
attacks ETF mechanics instead (spread, leveraged decay, premium/discount to NAV,
theme exhaustion).

## Excluding OTC

FinViz's screener universe covers listed venues only (AMEX, NASDAQ, NYSE, CBOE);
OTC and pink-sheet tickers are not in it. Three configurable strategies,
`screener.exchange_mode`:

| Mode | Behaviour | Cost |
|---|---|---|
| `universe` | no exchange token; rely on the FinViz universe plus a post-fetch guard that drops any row whose reported exchange is outside `allowed_exchanges` | 1 pass (default in public mode) |
| `explicit` | one pass with the multi-select token `exch_amex|nasd|nyse` | 1 pass (default in Elite mode) |
| `per_exchange` | one pass per exchange, merged and de-duplicated | 3 passes |

`auto` picks `explicit` in Elite mode and `universe` in public mode. Note that
multi-select within one filter category is an Elite feature, which is why the
public default does not rely on it.

## Data paths

| Mode | Endpoint | Notes |
|---|---|---|
| `elite` | `elite.finviz.com/export.ashx?...&auth=$FINVIZ_API_KEY` | CSV, complete result set, one request per view |
| `public` | `finviz.com/screener.ashx?...` | HTML parsed with BeautifulSoup, 20 rows per page, `screener.max_pages` pages (default 2), early stop on a short page |
| `fixture` | local JSON | offline replay for dry runs and tests |

Views are merged on ticker; the first view that supplies a field wins, later
views only fill gaps. `screener.request_delay_seconds` (default 1.5s) throttles
requests — the public endpoint rate-limits aggressively.

## Tuning guidance

- **Too few hits:** drop `ta_perf_dup`, relax relative volume to `sh_relvol_o1.5`,
  or widen price to `sh_price_1to30`.
- **Too many junk hits:** raise `sh_avgvol_o1000`, add `sh_price_o2` to leave the
  most dilution-prone band, or require `ta_highlow20d_b0to5h` so the move comes
  out of a tight range rather than a vertical run.
- **Chasing extension:** the screener cannot express "no more than 15% above the
  SMA20"; that judgement belongs to the Technician's `extension_pct_sma20` and the
  Judge's confidence, which is where it is applied.
