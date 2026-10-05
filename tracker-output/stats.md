# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 13 / unreviewed 0 · TAKE/SKIP 2/11 (15.4% TAKE)

**Account (every call):** $1,231.53 (+23.15% on $1,000.00) · 40.0% allocated · cash $799.16

**TAKE only (the Judge's scorecard):** $972.93 (-2.71%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +17.81% — equal weight across all 13 priced call(s)

**Generated:** 2026-10-05T14:28:17+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 13 |
| Reviewed calls | 13 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 2 |
| Shadow (SKIP) calls | 11 |
| Open | 4 |
| Right | 4 |
| Wrong | 6 |
| Neutral | 3 |
| Hit rate % | 30.8 |
| **Total PnL % (equal weight, all calls)** | +17.81% |
| Average PnL % per call | 17.81 |
| Portfolio PnL % (equal weight, TAKE only) | -13.53 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -36.21% — entry 7.58 → 4.835000038146973

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 13 | 4 | 4 | 6 | 3 | 30.8 | 17.81 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | 0.0 |
| stock | 12 | 3 | 4 | 6 | 2 | 33.3 | 19.29 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | 0.0 |
| squeeze | 12 | 3 | 4 | 6 | 2 | 33.3 | 19.29 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 2 | 1 | 0 | 1 | 1 | 0.0 | -13.53 |
| SKIP (shadow) | 11 | 3 | 4 | 5 | 2 | 36.4 | 23.51 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -37.04 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.88 | 4.56 | 0.32 | -0.204 | 13 | quality (higher is better) |
| technician | 4.88 | 4.33 | 0.54 | 0.063 | 13 | quality (higher is better) |
| skeptic | 8.12 | 7.39 | 0.74 | 0.353 | 13 | severity (lower is better) |
| risk_manager | 4.88 | 4.28 | 0.6 | 0.252 | 13 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 8 | 2 | 3 | 4 | 1 | 37.5 | 20.22 |
| 70-100 | 3 | 2 | 0 | 1 | 2 | 0.0 | -17.65 |


### Voided calls

Kept for the record, excluded from every figure above: these
could not have been executed, so they cannot have made or lost
anything.

| Ticker | Instrument | PnL % | Reason |
|---|---|---|---|
| NCPL | put | -27.06% | put: not executable — no listed options and no borrow on this name |
| SDEV | — | +0.00% | duplicate: created only because call 8 was falsely stopped on a pre-entry bar |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20261005T142600Z | 2026-10-05T14:26:00+00:00 | yes | 1 | 1 | 0.0 |
| run_20261005T133712Z | 2026-10-05T13:37:12+00:00 | yes | 1 | 1 | 0.0 |
| run_20261005T105502Z | 2026-10-05T10:55:02+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T094707Z | 2026-10-05T09:47:07+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T093900Z | 2026-10-05T09:39:00+00:00 | yes | 0 | 0 | 0.0 |

