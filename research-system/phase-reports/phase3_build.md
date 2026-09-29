# [DATA ENGINEER + DEVELOPER] Phase 3 — Build (checkpoint 1)

**Date:** 2026-09-29
**Status:** core pipeline built and verified. Three items are blocked on inputs from you (see the end).

## What "live data from CoinMarketCap" means here
- The **asset universe** is taken live from the official CoinMarketCap API (`/v1/cryptocurrency/listings/latest`). It is read fresh on every run, and the key is sent only in a request header.
- I am **not** scraping the coinmarketcap.com website. The official API returns the same numbers and is the permitted route. If you did mean the website itself, tell me and I'll check CMC's terms with you first.
- **Price history** comes from the exchange through ccxt. The free CMC plan has only about 1 month of history, and a backtest needs 3+ years.

## Components and verification

| # | Component | Role | Verified how | Result |
|---|---|---|---|---|
| 1 | `config/settings.example.yaml` + `rsys/safety.py` | DEVELOPER | 12 unit tests | ✅ Live mode needs 3 hand-set fields in *your* `settings.yaml`. The example file can never enable live, and configs holding exchange keys are refused |
| 2 | `rsys/universe.py` (CMC → filters → exchange pairs → history check) | DATA ENGINEER | 6 unit tests with CMC-shaped data | ✅ logic · ⏸ **live run waits for `CMC_API_KEY`** |
| 3 | `rsys/ohlcv.py` (ccxt download → canonical CSV → validation) | DATA ENGINEER | 4 unit tests + **live OKX download** | ✅ BTC/USDT and ETH/USDT, 1d and 4h, 2022-10-01 → 2026-09-29, **0 gaps, 0 bad rows** |
| 4 | `rsys/indicators.py` (shared SuperTrend) | DEVELOPER | 4 unit tests, including a no-look-ahead test | ✅ |
| 5 | freqtrade: `BuyAndHold`, `SuperTrendStrategy`, config generator | DEVELOPER | Docker `freqtrade 2026.8`: backtest, `lookahead-analysis`, dry-run start | ✅ Backtests run; **lookahead-analysis: no bias**; the bot starts with "Dry run is enabled" |
| 6 | `rsys/finrl_agent.py` (FinRL StockTradingEnv + SB3 PPO) | DEVELOPER | 5 unit tests + smoke training in the `rsys-finrl` Docker image | ✅ Trains and evaluates; splits don't overlap; the holdout is only scored with `--evaluate-holdout` |
| 7 | Docker: `docker-compose.yml`, `research` and `finrl` images, `freqtrade-paper` service | DEVELOPER | `docker compose config`, both images built, tests pass inside the image | ✅ |
| 8 | eliza report bot | DEVELOPER | — | ⏸ Needs a Telegram or Discord bot token and an LLM key |
| 9 | hummingbot experiment | DEVELOPER | — | Optional; waiting on your yes/no |

41 unit tests pass, both locally and inside the FinRL image.

## Decisions made while building (please object if any is wrong)
1. **Exchange = OKX.** Binance returns HTTP 451 (region block) from the build environment, and Kraken's public API only gives 720 candles. You can change `data.exchange` in `settings.yaml`.
2. **One canonical dataset.** Every engine reads candles exported from the same CSVs, so any difference between engines comes from the engine, not the data.
3. **Costs:** 0.10% fee plus 0.05% slippage per side, run in freqtrade as `--fee 0.0015`, with market orders on the far side of the spread. A 0.15% slippage stress test comes in Phase 4.
4. **FinRL install:** upstream FinRL pins ccxt 3.x and pulls in ray, selenium and jqdatasdk. It is installed with `--no-deps` from a pinned GitHub commit, together with an exact lock file of what its import chain needs. The PyPI release (0.3.7) is stale.
5. **FinRL "shares":** its environment only trades whole units, so prices are rescaled to about 100 units at the start of training. This does not change returns.

## Smoke-test numbers (**not evidence**; do not read as results)
These runs only prove the pipeline works. SuperTrend used **placeholder** parameters (ATR 10, ×3.0, 4h), in-sample, at 20% position size. FinRL trained for only 3–5k steps.

| Run | Window | Return | Notes |
|---|---|---|---|
| Buy-and-hold 50/50 BTC/ETH (freqtrade) | 2022-11 → 2026-09 | +188.9% | baseline |
| SuperTrend placeholder, BTC/USDT 4h (freqtrade) | 2022-11 → 2026-09 | +22.2% | 101 trades, 37.6% wins, 20% position size, max drawdown 7.05% |
| FinRL PPO, 3–5k steps (validation window) | 2025-04 → 2026-03 | −18% to −26% | buy-and-hold was −4.65% in the same window |

**Disclosure for the Reviewer:** these smoke runs covered the full period. That includes the locked holdout (2026-04 → 2026-09), which the first FinRL smoke run also scored. No parameter was chosen or changed because of these numbers. The Phase 4 report will repeat this disclosure.

## Blocked on you
1. **`CMC_API_KEY`**: add it as an environment variable in this cloud environment's settings, or in `research-system/.env` if you run it locally. Please don't paste it into chat.
2. **SuperTrend parameters**: ATR period, multiplier, timeframe, and any extra entry or exit rules. Until then the placeholders are clearly marked, and every run logs a warning.
3. **eliza**: Telegram or Discord, the bot token and channel or chat ID, and which LLM provider key to use (eliza needs one to talk). Tokens go in environment settings or `.env` only.
4. **hummingbot**: yes or no to the optional market-making paper experiment.
