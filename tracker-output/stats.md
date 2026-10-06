# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 14 / unreviewed 0 · TAKE/SKIP 2/12 (14.3% TAKE)

**Account (every call):** $1,187.86 (+18.79% on $1,000.00) · 50.0% allocated · cash $699.16

**TAKE only (the Judge's scorecard):** $970.57 (-2.94%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +13.42% — equal weight across all 14 priced call(s)

**Generated:** 2026-10-06T13:46:21+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 14 |
| Reviewed calls | 14 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 2 |
| Shadow (SKIP) calls | 12 |
| Open | 5 |
| Right | 5 |
| Wrong | 6 |
| Neutral | 3 |
| Hit rate % | 35.7 |
| **Total PnL % (equal weight, all calls)** | +13.42% |
| Average PnL % per call | 13.42 |
| Portfolio PnL % (equal weight, TAKE only) | -14.72 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -36.21% — entry 7.58 → 4.835000038146973

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 14 | 5 | 5 | 6 | 3 | 35.7 | 13.42 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.13 |
| stock | 13 | 4 | 4 | 6 | 3 | 30.8 | 14.44 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.13 |
| squeeze | 13 | 4 | 4 | 6 | 3 | 30.8 | 14.44 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 2 | 1 | 0 | 1 | 1 | 0.0 | -14.72 |
| SKIP (shadow) | 12 | 4 | 5 | 5 | 2 | 41.7 | 18.11 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -32.82 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.39 | 0.11 | -0.131 | 14 | quality (higher is better) |
| technician | 4.1 | 4.78 | -0.68 | 0.034 | 14 | quality (higher is better) |
| skeptic | 7.9 | 7.67 | 0.23 | 0.291 | 14 | severity (lower is better) |
| risk_manager | 4.7 | 4.06 | 0.64 | 0.295 | 14 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 8 | 2 | 3 | 4 | 1 | 37.5 | 18.78 |
| 70-100 | 4 | 3 | 1 | 1 | 2 | 25.0 | -21.28 |


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
| run_20261006T134542Z | 2026-10-06T13:45:42+00:00 | yes | 0 | 0 | 0.0 |
| run_20261006T125109Z | 2026-10-06T12:51:09+00:00 | yes | 0 | 0 | 0.0 |
| run_20261006T100352Z | 2026-10-06T10:03:52+00:00 | yes | 1 | 0 | 0.0 |
| run_20261006T073818Z | 2026-10-06T07:38:18+00:00 | no | 0 | 0 | 0.0 |
| run_20261006T064311Z | 2026-10-06T06:43:11+00:00 | no | 0 | 0 | 0.0 |

