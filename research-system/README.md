# Trading-vs-Investing Research System

An evidence-driven research pipeline that decides whether to focus on **TRADING** (short-term, active) or **INVESTING** (long-term allocation). It then builds, tests, risk-checks and critically reviews the chosen path. **Paper trading only.**

> ⚠️ Nothing in this directory places real orders. Live trading will only ever be possible after **you** edit your local config by hand (see "Safety" below). This is research, not financial advice.

## Status

| Phase | Role | Status | Output |
|---|---|---|---|
| 1 | RESEARCHER | ✅ Done | [phase1_researcher.md](phase-reports/phase1_researcher.md), [phase1_scores.json](data/phase1_scores.json) |
| 2 | STRATEGIST | ✅ Done (TRADING, confirmed) | [phase2_strategist.md](phase-reports/phase2_strategist.md) |
| 3 | DATA ENGINEER + DEVELOPER | 🔨 Checkpoint 1: core pipeline verified; waiting on CMC key, SuperTrend parameters, eliza tokens | [phase3_build.md](phase-reports/phase3_build.md) |
| 4 | BACKTESTER | ⏳ | freqtrade → jesse → nautilus_trader results |
| 5 | RISK MANAGER | ⏳ | Limits and veto report |
| 6 | REVIEWER | ⏳ | Final verdict |

## Layout

```
research-system/
├── config/settings.example.yaml  # all knobs; copy to settings.yaml (git-ignored) to change
├── .env.example                  # API keys go in .env (git-ignored), never in code
├── rsys/                         # Python package
│   ├── safety.py                 # paper-only lock
│   ├── universe.py               # live CoinMarketCap universe + filters
│   ├── ohlcv.py                  # ccxt candles -> canonical CSV (+ validation)
│   ├── indicators.py             # shared SuperTrend (same signals in every engine)
│   ├── freqtrade_config.py       # paper-only freqtrade configs
│   ├── finrl_agent.py            # FinRL PPO agent
│   └── cli.py                    # python -m rsys.cli ...
├── freqtrade/user_data/strategies/  # BuyAndHold, SuperTrendStrategy
├── docker/ + docker-compose.yml  # research, finrl, freqtrade, freqtrade-paper
├── data/phase1_scores.json       # Researcher scores (edit to re-run the decision)
├── data/universe/                # CMC universe snapshots (committed for audit)
├── data/ohlcv/                   # downloaded candles (git-ignored, re-downloadable)
├── scripts/decide.py             # Strategist decision rule
├── tests/                        # unit tests (python -m pytest tests)
└── phase-reports/                # one report per phase, labelled with the active role
```

## Setup

Requirements: Docker with Compose v2. Everything else runs inside containers.

```bash
cd research-system
cp .env.example .env               # then put your CoinMarketCap key in CMC_API_KEY
docker compose build research
docker compose build finrl         # large (torch); only needed for the RL agent

# 1. Universe (live from the CoinMarketCap API) and candles (ccxt, OKX by default)
docker compose run --rm research universe
docker compose run --rm research download
docker compose run --rm research export-freqtrade
docker compose run --rm research freqtrade-config   # dry_run is forced on

# 2. Backtests
docker compose run --rm freqtrade backtesting --config user_data/config.base.json \
    --config user_data/config.buyhold.json --fee 0.0015
docker compose run --rm freqtrade backtesting --config user_data/config.base.json \
    --config user_data/config.supertrend.json --fee 0.0015
docker compose run --rm freqtrade lookahead-analysis --config user_data/config.base.json \
    --config user_data/config.supertrend.json --fee 0.0015
docker compose run --rm finrl --timesteps 50000 --seeds 5   # validation window only

# 3. Paper trading bot (dry-run)
docker compose --profile paper up -d freqtrade-paper
```

Without Docker: `pip install -r requirements.txt`, then `python -m rsys.cli <command>` from `research-system/`.

If you sit behind a TLS-intercepting proxy, build with `--secret id=extra_ca,src=<ca.crt>`. The certificate is never copied into the image.

## Re-running the Phase 2 decision

```bash
python3 scripts/decide.py     # prints the decision as JSON
```

The rule:
- Each path gets the weighted mean of its tools' Phase 1 scores (the main engine counts twice).
- It loses 1 point for each Phase 4 validation engine that cannot trade its assets.
- A gap below 0.5 means "BOTH".

## How to read the results (applies from Phase 4 on)

- **Always compare to the baseline.** A strategy only counts if it beats buy-and-hold **out of sample** after fees and slippage.
- **Out-of-sample numbers only.** In-sample numbers are shown only to measure how much results drop from in-sample to out-of-sample. A large drop means overfitting.
- **Max drawdown** matters more than return. Ask yourself whether you could sit through that loss.
- **Sharpe / Sortino:** risk-adjusted return. Below about 0.5 out of sample is weak. Above about 3 on crypto usually means a bug or look-ahead.
- **Trade count:** fewer than about 30 out-of-sample trades is too few to trust.
- **Engine disagreement:** if freqtrade, jesse and nautilus differ by more than about 20% in return or in trade count on the same settings, the result is flagged until the cause is explained.
- **Survivorship label:** results on screened altcoin pairs are marked "optimistic". BTC/ETH results are the primary evidence.
- **Locked holdout:** the last 6 months (2026-04 → 2026-09) are scored only in the final Backtester run.

## Safety

- Every engine runs in paper, dry-run or backtest mode. Exchange API keys are never needed or stored.
- Live mode is possible only if **you** put all three of these lines in your own `config/settings.yaml`:
  ```yaml
  trading_mode: live
  live_trading_enabled: true
  live_trading_ack: "I ACCEPT REAL MONEY RISK"
  ```
  The example file can never enable live mode, and no script, agent or CI job writes these fields.
- The config generator refuses any freqtrade config that has `dry_run` off, or that contains exchange credentials, unless that lock is open.
- API keys (CoinMarketCap, Telegram/Discord, LLM) are read only from environment variables or `.env`.
- The eliza bot (coming next) gets read-only access to reports and no wallet or trading plugins.
