# Trading-vs-Investing Research System

An evidence-driven research pipeline that decides whether to focus on **TRADING** (short-term, active) or **INVESTING** (long-term allocation). It then builds, tests, risk-checks and critically reviews the chosen path. **Paper trading only.**

> ⚠️ Nothing in this directory places real orders. Live trading will only ever be possible after **you** edit your local config by hand (see "Safety" below). This is research, not financial advice.

## Status

| Phase | Role | Status | Output |
|---|---|---|---|
| 1 | RESEARCHER | ✅ Done | [phase-reports/phase1_researcher.md](phase-reports/phase1_researcher.md), [data/phase1_scores.json](data/phase1_scores.json) |
| 2 | STRATEGIST | ✅ Done, ⏸ **awaiting your confirmation** | [phase-reports/phase2_strategist.md](phase-reports/phase2_strategist.md) |
| 3 | DATA ENGINEER + DEVELOPER | ⏳ Not started | Docker stack, ccxt/CMC pipelines, strategies |
| 4 | BACKTESTER | ⏳ | freqtrade → jesse → nautilus_trader results |
| 5 | RISK MANAGER | ⏳ | Limits and veto report |
| 6 | REVIEWER | ⏳ | Final verdict |

**Current decision:** TRADING (crypto). Net score 7.57 vs 4.17. See the Phase 2 report for the reasoning and for what I need from you.

## Layout

```
research-system/
├── data/phase1_scores.json   # Researcher scores and facts (edit to re-run the decision)
├── scripts/decide.py         # Strategist decision rule (stdlib only)
├── tests/test_decide.py      # Tests for the decision rule
└── phase-reports/            # One report per phase, labelled with the active role
```

## Re-running the decision

```bash
python3 research-system/scripts/decide.py            # prints the decision as JSON
python3 -m pytest research-system/tests -q           # tests for the decision rule
```

To challenge the decision, change a score or weight in `data/phase1_scores.json` and re-run. The rule is:

- Each path's score is the weighted mean of its core tools' scores (the main engine counts twice).
- One point is subtracted for each Phase 4 validation engine that cannot trade that path's assets.
- A gap below 0.5 means "BOTH".

## How to read the results (applies from Phase 4 on)

- **Always compare to the baseline.** A strategy only counts if it beats buy-and-hold **out of sample** after fees and slippage.
- **Out-of-sample numbers only.** In-sample numbers are shown only to measure how much results drop from in-sample to out-of-sample. A large drop means overfitting.
- **Max drawdown** matters more than return. Ask yourself whether you could sit through that loss.
- **Sharpe / Sortino:** risk-adjusted return. Below about 0.5 out of sample is weak. Above about 3 on crypto usually means a bug or look-ahead.
- **Trade count:** fewer than about 30 out-of-sample trades is too few to trust.
- **Engine disagreement:** if freqtrade, jesse and nautilus differ by more than about 20% in return or in trade count on the same settings, the result is flagged until the cause is explained.
- **Survivorship label:** results on screened altcoin pairs are marked "optimistic". BTC/ETH results are the primary evidence.

## Safety (planned for Phase 3)

- Every engine runs in paper, dry-run or backtest mode. Exchange API keys are never needed.
- Live mode needs **both** of these, typed by you in your local, git-ignored config:
  - `live_trading_enabled: true`
  - a `live_trading_ack` phrase
- No script, agent or CI job writes those fields.
- API keys (CoinMarketCap, Telegram/Discord) are only read from a git-ignored `.env` file. Claude will ask you for them and will never hardcode them.
- The eliza bot has its wallet and trading plugins removed and can only read reports.
