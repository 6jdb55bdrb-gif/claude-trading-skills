# [RESEARCHER] Phase 1 — Tool and Screener Evaluation

**Date:** 2026-09-29
**Role rules:** the Researcher collects facts and gives scores. It makes no decisions.
**Machine-readable scores:** [`../data/phase1_scores.json`](../data/phase1_scores.json)

Sources: each project's public GitHub page (stars, forks, open issues and license, read on 2026-09-29), the freqtrade and FinRL release and commit pages, the CoinMarketCap API pricing page, the Finviz Elite page, the financialdatasets.ai pricing page, and the Jesse docs and help pages. Star counts are rounded as GitHub shows them.

## Summary table

| Tool | Built for | Maturity signals | Solo non-coder (1–10) | TRADING | INVESTING |
|---|---|---|---|---|---|
| ccxt | Trading (crypto) | 44.2k★, MIT, ~101k commits, 100+ exchanges | 6 | **9** | 4 |
| freqtrade | Trading (crypto) | 54.9k★, 22 open issues, monthly releases (2026.8 on 2026-08-31) | 7 | **9** | 3 |
| jesse | Trading (crypto) | 8.6k★, 7 open issues, PyPI-only releases | 6 | 7 | 2 |
| nautilus_trader | Both (multi-asset) | 29.5k★, releases every two weeks, LGPL-3.0, v2 API still changing | 3 | 8 | 5 |
| hummingbot | Trading (market making) | 20.3k★, Apache-2.0, 50+ connectors | 6 | 6 | 1 |
| FinRL | Both (research) | 16.4k★, **283 open issues**, active commits in Sept 2026 | 3 | 4 | 6 |
| ai-hedge-fund | Investing (LLM agents) | 63.8k★, educational proof of concept | 7 | 2 | 5 |
| eliza | Neither (agent framework) | 19.5k★, TypeScript monorepo | 5 | 3 | 3 |
| Finviz Elite | Investing (US stocks/ETFs) | Commercial, $299.50/yr | 8 | 3 | 7 |
| CoinMarketCap API | Both (crypto) | Commercial; free tier has 15k credits/month | 8 | 7 | 4 |

## Per-tool findings

### ccxt — TRADING 9 / INVESTING 4
- **Purpose:** one API for 100+ crypto exchanges. It fetches market data (OHLCV, order books) and places orders.
- **Why 9 for trading:** it is the standard library for this, freqtrade already uses it inside, and it can download years of free candle data from major exchanges.
- **Why 4 for investing:** it covers crypto only, with no equities and no fundamentals.
- **Limitations and risks:** it is a library, not an app. How much history you get and the rate limits depend on each exchange. Some regions block some exchanges (Binance, for example), so the data exchange must be one you can reach.
- **Cost:** free (MIT).

### freqtrade — TRADING 9 / INVESTING 3
- **Purpose:** a complete crypto trading bot with paper mode (`dry_run`), backtesting, hyperopt, a Telegram bot, a web UI and Docker images.
- **Why 9:** it is the most mature project in the list, with monthly releases and few open issues. It has built-in `lookahead-analysis` and `recursive-analysis` commands, which directly test for the look-ahead bias the Backtester has to rule out. Fees are modelled in backtests. Paper trading is the default setting.
- **Why 3 for investing:** it has no portfolio weights or rebalancing model.
- **Limitations and risks:** backtests run on candles, so fills are approximate. Hyperopt makes curve fitting very easy. Strategies are Python files, but you can copy and edit templates.
- **Cost:** free (GPL-3.0).

### jesse — TRADING 7 / INVESTING 2
- **Purpose:** a crypto strategy framework with a clean backtester, Monte Carlo testing and rule-significance testing.
- **Why 7:** it makes a good independent cross-check of freqtrade on the same candles.
- **Limitations and risks:** paper and live trading need Jesse's live-trade plugin and a license key. A limited free tier exists, and the premium license has been listed at about $1,600. **Backtesting is free, and backtesting is all this project needs Jesse for.** It covers crypto only, so it **cannot cross-check a stock portfolio**. Its community is smaller.

### nautilus_trader — TRADING 8 / INVESTING 5
- **Purpose:** a high-fidelity event-driven engine with a Rust core and a Python API. It works at nanosecond resolution on order-book and tick data, and the same code runs in backtests and live.
- **Why 8:** it is the best "final exam" engine for a strategy.
- **Why 5 for investing:** it trades equities through Interactive Brokers, but good equity data (Databento) is paid, and it has no portfolio optimiser.
- **Limitations and risks:** it is the hardest tool here to learn (usability 3). Breaking changes can land between releases, and the maintainers say v2 release candidates should not be used for real capital.

### hummingbot — TRADING 6 / INVESTING 1
- **Purpose:** market making and arbitrage on centralised and decentralised exchanges. It has a real paper-trade connector.
- **Why only 6:** a market-making edge depends on fee tier, latency, queue position and inventory risk. A retail user does not control these, and backtests on candles cannot model them. **Paper market-making results come out systematically too optimistic.**
- **Cost:** free (Apache-2.0).

### FinRL — TRADING 4 / INVESTING 6
- **Purpose:** deep reinforcement learning (PPO, A2C, SAC, TD3, DDPG) for stock or crypto trading and portfolio allocation.
- **Why 6 for investing:** its portfolio-allocation environment fits monthly rebalancing research well.
- **Why 4 for trading:** RL results on crypto candles vary heavily with the random seed and the time period.
- **Limitations and risks:** the project calls itself an educational research framework and points production users to FinRL-X. It has 283 open issues and its dependencies change often (PyTorch, Stable-Baselines3, pandas). RL overfits easily, so every result needs several seeds and walk-forward testing. It is hard to use without coding (usability 3).

### ai-hedge-fund — TRADING 2 / INVESTING 5
- **Purpose:** LLM "investor persona" agents that analyse stocks. It is educational and does not trade.
- **Why only 5 even for investing:** its backtests are **structurally contaminated**. The LLM read about what later happened to these stocks during training, and the project can only partly hide that. Runs are not reproducible and cost money every time.
- **Cost:** financialdatasets.ai has **no free tier** ($20 for 1,000 requests, or $200/month). You also need an LLM API key.

### eliza — TRADING 3 / INVESTING 3 (neutral)
- **Purpose:** a TypeScript agent framework with Telegram and Discord connectors.
- **Role here:** a report and alert bot only, so it is neutral between the paths.
- **Risks:** it ships with wallet and on-chain actions, which must be removed so it can never trade. It is a heavy framework for sending reports. freqtrade's own Telegram bot already covers basic alerts. It no longer accepts third-party plugins.

### Finviz Elite — TRADING 3 / INVESTING 7
- **Purpose:** a US stock and ETF screener. CSV/API export is **Elite-only** ($39.50/month or $299.50/year).
- **Why 7 for investing:** the fundamental and valuation filters are excellent and easy to export.
- **Critical limitation:** it returns **today's snapshot only**, with no point-in-time history. Running today's screen over past years gives **survivorship and look-ahead bias**, because it picks stocks that are large and profitable *now*.
- **Scraping:** scraping the free site may breach Finviz's terms. **Nothing will be scraped without your explicit permission.**

### CoinMarketCap API — TRADING 7 / INVESTING 4
- **Purpose:** crypto rankings, market cap, 24h volume and stablecoin tags. Good for building a liquid universe.
- **Free Basic plan:** 15,000 credits/month, 50 requests/minute, and only about **1 month of history**.
- **Critical limitation:** on the free plan you cannot rebuild what the top 50 looked like three years ago. Backtesting today's top 50 over three years is **survivorship bias**, because it leaves out coins that collapsed. The Builder plan ($29/month) has 3 years of history.

## Cross-cutting facts the Strategist should weigh
1. **Can results be cross-checked?** Phase 4 requires primary engine → jesse → nautilus. For crypto, all three engines work. For equities, jesse cannot run at all, so only 2 of 3 are possible.
2. **Minimum data cost:** the crypto path costs $0/year (exchange candles plus the free CMC plan). The equity path costs at least about $320/year (Finviz Elite plus financialdatasets), plus LLM tokens.
3. **Bias exposure:** both screeners give only current snapshots on the plans assumed here. The equity path adds a second source of look-ahead through the LLM agents.
4. **Built-in bias tooling:** only freqtrade ships automatic look-ahead detection.
