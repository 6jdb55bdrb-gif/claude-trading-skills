# Silver Bullet Backtest Results (2026-11-05 snapshot)

## Run Setup

**Command**
`backtest_silver_bullet.py --days 730 --grid` with the default symbols and the 1m/5m/15m timeframes.

**Rules**
- Canonical rules: sweep + MSS + displacement ≥ 0.5 ATR.
- Entry at the FVG edge.
- Target at the opposing pre-window liquidity, minimum 1.5R.
- No bias filter.
- Positions flat 60 min after the window.

**Costs**
- BTC: 2 bp per side.
- ETFs/futures: 0.5 bp per side.
- Setups costing more than 0.10R round trip are skipped.

**Data**

| Instrument | Source | History |
|---|---|---|
| BTC | Binance BTCUSDT | 730 days (Nov 2024 – Nov 2026) at every timeframe |
| SPY, QQQ, ES=F, NQ=F | Yahoo | 1m: ~28 days; 5m/15m: ~58 days |

ETFs have no 03:00 London window (pre-market starts at 04:00). The futures do.

## Canonical Configuration

| Symbol | TF | Trades | Win% | Exp R | 95% CI | PF | H1 / H2 Exp | Grid+ | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| BTC | 1m | 183 | 39% | −0.086 | [−0.26, 0.10] | 0.85 | −0.02 / −0.17 | 24% | NO_EDGE |
| BTC | 5m | 18 | 33% | −0.233 | [−0.57, 0.10] | 0.45 | 0.05 / −0.52 | 18% | INSUFFICIENT_SAMPLE |
| BTC | 15m | 0 | – | – | – | – | – | – | INSUFFICIENT_SAMPLE |
| SPY | 1m | 10 | 30% | 0.089 | [−1.06, 1.41] | 1.12 | 0.73 / −0.19 | 50% | INSUFFICIENT_SAMPLE |
| QQQ | 1m | 11 | 36% | −0.050 | [−0.86, 0.82] | 0.93 | −0.34 / 0.30 | 7% | INSUFFICIENT_SAMPLE |
| ES | 1m | 9 | 33% | 0.114 | [−1.05, 1.31] | 1.16 | 0.81 / −0.24 | 69% | INSUFFICIENT_SAMPLE |
| NQ | 1m | 19 | 32% | −0.340 | [−0.79, 0.19] | 0.53 | −0.34 / −0.34 | 23% | INSUFFICIENT_SAMPLE |
| SPY/QQQ/ES/NQ | 5m | 1–3 | – | – | – | – | – | 5–39% | INSUFFICIENT_SAMPLE |
| all | 15m | 0 | – | – | – | – | – | 0% (BTC) | INSUFFICIENT_SAMPLE |

## BTC 1m by Window

| Window | Trades | Exp R |
|---|---|---|
| London | 12 | −0.05 |
| AM | 124 | −0.13 |
| PM | 47 | +0.03 |

## BTC 1m Exits

- 18 targets hit
- 92 stops hit
- 73 time exits

The pre-window liquidity target is reached only about 10% of the time within the hold period.

## Conclusions

1. **No robust edge.** No asset × timeframe reaches `ROBUST_EDGE`. The longest, most reliable sample (BTC 1m, 2 years, 183 trades) is about breakeven gross (−0.01R). It is negative after costs, with the second half worse than the first.
2. **The "best" configurations are noise.** The top grid cell differs by instrument (for example, CE/bias on BTC, fixed 2R on ES, MSS on QQQ). The median grid expectancy is ≤ 0 for most instruments. Picking a best cell would be curve-fitting.
3. **Costs dominate on 1m.** The median BTC 1m stop was about 23 bp, so a 4 bp round trip costs about 0.17R. The first iteration (no `max_cost_r` filter, no pre-window sweep allowance) lost −0.28R per trade net while being only −0.05R gross.
4. **Timeframe matters structurally.** The setup needs a sweep, a 3-candle FVG and a retrace fill inside one hour. On 15m bars (4 per window) it almost never completes, and on 5m it is rare. The Silver Bullet is a 1m–3m execution model.
5. **Equity samples are too small.** With 28–58 days of Yahoo intraday data, equity results cannot confirm or reject the strategy. Use longer CSV exports (broker or futures data) via `csv:` sources before drawing conclusions.
6. **Candidate for forward testing only.** Relaxing MSS and adding the daily-trend bias (`--no-mss --bias sma`) was positive on BTC 1m (+0.04R, 128 trades) and BTC 5m (+0.20R, 46 trades). Both 95% CIs include 0, and the variant was found by looking at the data. Treat it as a hypothesis to paper-trade, not an edge.

Backtests are hypothetical and do not guarantee future results.
