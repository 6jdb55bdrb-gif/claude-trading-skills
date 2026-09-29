# [STRATEGIST] Phase 2 — Decision: TRADING vs INVESTING

**Date:** 2026-09-29
**Input:** [Phase 1 Researcher report](phase1_researcher.md) and [`../data/phase1_scores.json`](../data/phase1_scores.json)
**Reproduce:** `python3 research-system/scripts/decide.py`
**Status:** ⏸ **Waiting for your confirmation before Phase 3.**

## Decision: **TRADING** (crypto, paper only)

| Path | Weighted tool-stack score | Engines that can validate it | Penalty | Net score | Minimum data cost per year |
|---|---|---|---|---|---|
| **TRADING** | 7.57 | 3 of 3 (freqtrade, jesse, nautilus) | 0 | **7.57** | $0 |
| INVESTING | 5.17 | 2 of 3 (jesse cannot run equities) | −1.0 | **4.17** | about $320 plus LLM tokens |

How the numbers are built: each score is the weighted mean of the core tools' Phase 1 scores for that path, with the main engine counted twice. One point is subtracted for each Phase 4 validation engine that cannot trade the path's asset class. A gap smaller than 0.5 would have meant "BOTH". The actual gap is **3.4**.

### Why
1. **Stronger foundation:** freqtrade and ccxt are the most mature, most actively maintained tools in the list, and freqtrade has paper mode and look-ahead detection built in. The core of the investing path, FinRL and ai-hedge-fund, describes itself as research or educational code.
2. **Can be verified:** only the crypto path can run your full Phase 4 chain (freqtrade → jesse → nautilus). On equities, jesse cannot cross-check anything.
3. **Cleaner evidence:** ai-hedge-fund backtests carry LLM look-ahead that we cannot remove, and Finviz has no point-in-time history. The trading path has one bias to manage (the CMC universe), and we can keep it away from the main evidence.
4. **Cost:** $0 against about $320/year or more before you learn anything.

### What this decision does **not** mean
It is a judgment about **which toolset can produce reliable evidence**, not a prediction that active trading will make money. Studies of retail short-term traders mostly find underperformance after costs. That is why buy-and-hold BTC/ETH is the baseline every strategy must beat out of sample. If nothing beats it, the Reviewer will conclude that you should **invest (hold) rather than trade**, and that is a fully valid result.

## Repos: keep or drop

| Repo | Decision | Role |
|---|---|---|
| ccxt | ✅ Keep | Historical OHLCV and market data |
| freqtrade | ✅ Keep | Main engine: backtests, dry-run paper trading, look-ahead checks |
| jesse | ✅ Keep (backtest only) | Cross-check engine. No live-trade plugin and no license needed |
| nautilus_trader | ✅ Keep | High-fidelity validation of the best strategy only |
| FinRL | ✅ Keep (as a test subject) | RL agent strategy, treated sceptically: several seeds, strict walk-forward |
| eliza | ✅ Keep (restricted) | Daily report and alert bot. Wallet and trading plugins removed; read-only access to results |
| hummingbot | 🟡 Optional, later | One paper market-making experiment on BTC/USDT, only after the core results exist. Results labelled "optimistic by construction" |
| ai-hedge-fund | ❌ Drop | Stocks only, paid data, results polluted by LLM look-ahead, cannot be walk-forward tested |

## Screeners
- **CoinMarketCap: used.** Needs your free API key in Phase 3.
- **Finviz: not used.** The investing path was not chosen, and it would add cost and survivorship bias. No scraping will happen.

## Asset universe (CoinMarketCap filters)
| Filter | Value | Reason |
|---|---|---|
| Rank | Top 50 by market cap | Liquid, established assets |
| 24h volume | ≥ $50M | Keeps slippage small at paper-trading sizes |
| Exclude | Stablecoins (CMC `stablecoin` tag plus a manual list), wrapped or bridged tokens (WBTC, stETH and similar), exchange tokens with no spot pair on the data exchange | Avoids near-duplicate or non-tradable assets |
| Tradable | Has a `/USDT` spot pair on the chosen data exchange with ≥ 3 years of daily candles | Needed for 3-year walk-forward tests |
| Always included | BTC/USDT, ETH/USDT | Core pairs, no survivorship issue |
| Cap | At most 15 pairs after filters | Keeps backtests fast and results readable |

**Bias control:** the CMC free plan cannot tell us what the top 50 looked like in past years. So:
- **Primary evidence** comes from BTC/USDT and ETH/USDT only. Both were in the top 2 throughout the test window.
- **Screened altcoin pairs** are reported separately and labelled **"survivorship-biased (optimistic)"**.
- Optional: the CMC Builder plan ($29/month) would give 3 years of rankings, so the universe could be rebuilt month by month. I recommend against paying for it at this stage.

## Strategy set for Phase 3–4
1. **Baseline:** buy-and-hold BTC/USDT, buy-and-hold ETH/USDT, and a 50/50 BTC/ETH mix rebalanced monthly.
2. **SuperTrend on BTC/USDT** with your parameters (**needed from you:** ATR period, multiplier, timeframe, and any filters or exits).
3. **FinRL RL agent** (PPO; at least 5 seeds; fixed train/validation/test windows).
4. Optional: hummingbot paper market-making on BTC/USDT.

**Test design (for the Backtester):** at least 3 years of data (for example 2022-10 → 2026-09). Rolling walk-forward: 12 months in-sample and 3 months out-of-sample. The final 6 months stay locked as a holdout that nothing is tuned on. Fees of 0.1% per side; slippage of 0.05% per side, with a 0.15% stress test. Every cost setting is identical across engines.

**Risk limits (the Risk Manager will enforce these in Phase 5):** at most 20% of equity per position, a hard stoploss on every trade, a daily loss stop of 3%, and a portfolio drawdown stop of 20%. Leverage and futures are disabled.

## Paper-only safety design (to be built in Phase 3)
- `config/settings.yaml` has `trading_mode: paper`. The code **refuses to start live** unless *you* make both of these changes: set `live_trading_enabled: true` **and** add a hand-typed `live_trading_ack` phrase to your local, git-ignored config. No script, agent or CI job will ever write those fields.
- freqtrade runs with `dry_run: true`, and no exchange keys are ever needed for paper or backtests.
- eliza gets only read access to the reports folder.

## I need from you before Phase 3
1. ✅ or ✏️ on this decision (TRADING), the kept and dropped repos, and the universe filters.
2. Your **SuperTrend parameters**.
3. Your **CoinMarketCap free API key**. I'll ask for it at build time; it goes into a git-ignored `.env`, never into the repo.
4. Which **exchange** to use for ccxt candles (default Binance; Kraken or OKX if Binance is restricted where you live).
5. Whether you want the optional hummingbot experiment, and whether eliza should post to Telegram or Discord.
