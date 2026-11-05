---
layout: default
title: "ICT Silver Bullet"
grand_parent: English
parent: Skill Guides
nav_order: 36
lang_peer: /ja/skills/ict-silver-bullet/
permalink: /en/skills/ict-silver-bullet/
generated: true
---

# ICT Silver Bullet
{: .no_toc }

Mechanical ICT Silver Bullet strategy (NY 03-04 / 10-11 / 14-15 windows, liquidity sweep, displacement fair value gap, FVG retrace entry, opposing-liquidity target) with a conservative, look-ahead-free intraday backtester. Tests BTC, SPY, QQQ, ES and NQ across 1m/5m/15m with walk-forward halves, bootstrap confidence intervals and a 96-config sensitivity grid. Use when the user asks about the ICT Silver Bullet, fair value gap entries, killzone/time-window strategies, or wants to backtest or validate an ICT setup on crypto, index ETFs or index futures.
{: .fs-6 .fw-300 }

<span class="badge badge-free">No API</span>

[Download Skill Package (.skill)](https://github.com/tradermonty/claude-trading-skills/raw/main/skill-packages/ict-silver-bullet.skill){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View Source on GitHub](https://github.com/tradermonty/claude-trading-skills/tree/main/skills/ict-silver-bullet){: .btn .fs-5 .mb-4 .mb-md-0 }

<details open markdown="block">
  <summary>Table of Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## 1. Overview

Turn the discretionary ICT Silver Bullet into explicit rules and test whether
it has an edge after costs. The engine (`scripts/silver_bullet.py`) detects
setups bar by bar with no look-ahead and simulates fills conservatively. The
runner (`scripts/backtest_silver_bullet.py`) runs the setup across symbols and
timeframes. Each result gets a robustness verdict: `ROBUST_EDGE`,
`POSITIVE_UNCONFIRMED`, `UNSTABLE`, `NO_EDGE` or `INSUFFICIENT_SAMPLE`.

The full rule set is in `references/silver_bullet_rules.md`. The latest
multi-asset results are in `references/backtest_results.md`.

---

## 2. When to Use

- The user asks what the ICT Silver Bullet is or how to trade it mechanically.
- The user wants to backtest the Silver Bullet (or FVG retrace entries) on BTC, SPY, QQQ, ES, NQ or their own CSV data.
- The user asks which window (London / AM / PM) or timeframe works best.
- Before trading an ICT setup live, to check whether it survives costs and parameter changes.

---

## 3. Prerequisites

- Python 3.10+ with `pandas`, `numpy`, `requests` (see `requirements.txt`).
- `yfinance` (optional). It is needed only for `yahoo:` sources. `binance:` and `csv:` sources work without it (missing yfinance → exit 2).
- No API keys. Data sources:
  - Binance public market-data mirror (`data-api.binance.vision`): years of 1m crypto data.
  - Yahoo Finance: 1m data for about 30 days, 5m/15m for about 60 days.
  - Local CSV.

---

## 4. Quick Start

```bash
python3 skills/ict-silver-bullet/scripts/backtest_silver_bullet.py \
  --symbols BTC=binance:BTCUSDT,SPY=yahoo:SPY,QQQ=yahoo:QQQ,ES=yahoo:ES=F,NQ=yahoo:NQ=F \
  --timeframes 1m,5m,15m --days 730 --grid --output-dir reports/
```

---

## 5. Workflow

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

---

## 6. Resources

**References:**

- `skills/ict-silver-bullet/references/backtest_results.md`
- `skills/ict-silver-bullet/references/silver_bullet_rules.md`

**Scripts:**

- `skills/ict-silver-bullet/scripts/backtest_silver_bullet.py`
- `skills/ict-silver-bullet/scripts/data_sources.py`
- `skills/ict-silver-bullet/scripts/silver_bullet.py`
