---
name: ict-silver-bullet
description: Mechanical ICT Silver Bullet strategy (NY 03-04 / 10-11 / 14-15 windows, liquidity sweep, displacement fair value gap, FVG retrace entry, opposing-liquidity target) with a conservative, look-ahead-free intraday backtester. Tests BTC, SPY, QQQ, ES and NQ across 1m/5m/15m with walk-forward halves, bootstrap confidence intervals and a 96-config sensitivity grid. Use when the user asks about the ICT Silver Bullet, fair value gap entries, killzone/time-window strategies, or wants to backtest or validate an ICT setup on crypto, index ETFs or index futures.
---

# ICT Silver Bullet

## Overview

Turn the discretionary ICT Silver Bullet into explicit rules and test whether
it has an edge after costs. The engine (`scripts/silver_bullet.py`) detects
setups bar by bar with no look-ahead and simulates fills conservatively. The
runner (`scripts/backtest_silver_bullet.py`) runs the setup across symbols and
timeframes. Each result gets a robustness verdict: `ROBUST_EDGE`,
`POSITIVE_UNCONFIRMED`, `UNSTABLE`, `NO_EDGE` or `INSUFFICIENT_SAMPLE`.

The full rule set is in `references/silver_bullet_rules.md`. The latest
multi-asset results are in `references/backtest_results.md`.

## When to Use

- The user asks what the ICT Silver Bullet is or how to trade it mechanically.
- The user wants to backtest the Silver Bullet (or FVG retrace entries) on BTC, SPY, QQQ, ES, NQ or their own CSV data.
- The user asks which window (London / AM / PM) or timeframe works best.
- Before trading an ICT setup live, to check whether it survives costs and parameter changes.

## Prerequisites

- Python 3.10+ with `pandas`, `numpy`, `requests` (see `requirements.txt`).
- `yfinance` (optional). It is needed only for `yahoo:` sources. `binance:` and `csv:` sources work without it (missing yfinance → exit 2).
- No API keys. Data sources:
  - Binance public market-data mirror (`data-api.binance.vision`): years of 1m crypto data.
  - Yahoo Finance: 1m data for about 30 days, 5m/15m for about 60 days.
  - Local CSV.

## Workflow

### Step 1: Explain the Rules

Read `references/silver_bullet_rules.md`, then summarise the rules for the user:

- the three NY windows
- the pre-window liquidity range
- the sweep, displacement FVG and MSS
- the FVG-edge entry, the stop beyond the sweep, and the opposing-liquidity target

State the discretionary parts the model does not cover (HTF bias nuance, news days).

### Step 2: Run the Backtest

```bash
python3 skills/ict-silver-bullet/scripts/backtest_silver_bullet.py \
  --symbols BTC=binance:BTCUSDT,SPY=yahoo:SPY,QQQ=yahoo:QQQ,ES=yahoo:ES=F,NQ=yahoo:NQ=F \
  --timeframes 1m,5m,15m --days 730 --grid --output-dir reports/
```

Useful variations:

```bash
# Single window, fixed 2R target, CE (midpoint) entries
python3 skills/ict-silver-bullet/scripts/backtest_silver_bullet.py \
  --symbols NQ=yahoo:NQ=F --timeframes 1m --windows am \
  --target-mode rr --rr-target 2 --entry-mode ce --output-dir reports/

# Trade only with the daily trend, no MSS requirement
python3 skills/ict-silver-bullet/scripts/backtest_silver_bullet.py \
  --symbols BTC=binance:BTCUSDT --timeframes 1m,5m --bias sma --no-mss --output-dir reports/

# Your own data (timestamp,open,high,low,close; UTC unless offset given)
python3 skills/ict-silver-bullet/scripts/backtest_silver_bullet.py \
  --symbols MNQ=csv:data/mnq_1m.csv --timeframes 1m --cost-bps MNQ=0.3 --output-dir reports/
```

Downloads are cached in `.cache/ict-silver-bullet/` (git-ignored), so reruns are
reproducible and work offline. A full run with `--grid` takes about 6 minutes,
mostly spent downloading two years of BTC 1m data.

### Step 3: Interpret the Results

1. Lead with the **verdict** column, not the best number. `ROBUST_EDGE` needs all of the following:
   - at least 30 trades
   - a bootstrap 95% CI above 0
   - both halves positive
   - at least 60% of grid neighbours profitable
2. Use `Grid+` to tell a real edge from a lucky parameter choice. If the best configuration differs by instrument and the median grid expectancy is ≤ 0, the "best" result is noise.
3. Use the per-window table to show where the losses come from.
4. Flag sample-size limits. Yahoo caps equity intraday history at 30–60 days, so equity verdicts are usually `INSUFFICIENT_SAMPLE`. Suggest exporting longer broker/futures data to CSV.
5. On 15m charts the Silver Bullet rarely completes inside a one-hour window (4 bars). Treat it as a 1m–5m model.

### Step 4: Report

Save the generated `reports/ict_silver_bullet_backtest_<date>.md/.json`.
Summarise the following for the user:

- the verdict per asset × timeframe
- expectancy in R with its CI
- the per-window split
- the honest bottom line: whether the evidence supports trading it

Never present a single best grid cell as the strategy.

## Output Format

- Markdown: a summary table (trades, win %, expectancy R, 95% CI, PF, total R, max DD, first/second-half expectancy, Grid+, verdict), a per-window breakdown, best/worst grid configurations, and a verdict legend.
- JSON: parameters, stats per run, half splits, per-window stats, the full grid, and per-trade rows (unless `--no-trades`).

## Key Parameters

| Flag | Default | Meaning |
|---|---|---|
| `--windows` | london,am,pm | NY windows to trade |
| `--entry-mode` | edge | `edge` = FVG proximal edge, `ce` = FVG midpoint |
| `--target-mode` / `--min-rr` | liquidity / 1.5 | opposing pre-window liquidity, at least 1.5R |
| `--no-sweep`, `--no-mss` | off | relax the sweep / market-structure-shift requirement |
| `--displacement-atr` | 0.5 | displacement candle body ≥ x·ATR(14) |
| `--sweep-lead-minutes` | 30 | sweep may start 30 min before the window (e.g. the 09:30 open) |
| `--bias` | none | `sma`: longs only above the 20-day SMA, shorts only below |
| `--max-cost-r` | 0.10 | skip setups where the round-trip cost exceeds 0.10R |
| `--cost-bps` | binance 2, yahoo 0.5 | per-side cost override `NAME=bps` |

## Resources

- `scripts/silver_bullet.py`: strategy engine (setup detection, fill simulation, statistics).
- `scripts/data_sources.py`: Binance / Yahoo / CSV loaders with caching.
- `scripts/backtest_silver_bullet.py`: multi-asset runner, grid, verdicts, reports.
- `references/silver_bullet_rules.md`: the exact mechanical rules and simulation conventions.
- `references/backtest_results.md`: the latest multi-asset results and conclusions.
