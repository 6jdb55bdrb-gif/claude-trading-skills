# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 12 / unreviewed 0 · TAKE/SKIP 2/10 (16.7% TAKE)

**Account (every call):** $1,262.31 (+26.23% on $1,000.00) · 40.0% allocated · cash $835.37

**TAKE only (the Judge's scorecard):** $972.01 (-2.80%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +21.86% — equal weight across all 12 priced call(s)

**Generated:** 2026-10-05T13:39:16+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 12 |
| Reviewed calls | 12 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 2 |
| Shadow (SKIP) calls | 10 |
| Open | 4 |
| Right | 4 |
| Wrong | 5 |
| Neutral | 3 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +21.86% |
| Average PnL % per call | 21.86 |
| Portfolio PnL % (equal weight, TAKE only) | -14.0 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 12 | 4 | 4 | 5 | 3 | 33.3 | 21.86 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 12 | 4 | 4 | 5 | 3 | 33.3 | 21.86 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 12 | 4 | 4 | 5 | 3 | 33.3 | 21.86 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 2 | 1 | 0 | 1 | 1 | 0.0 | -14.0 |
| SKIP (shadow) | 10 | 3 | 4 | 4 | 2 | 40.0 | 29.03 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -43.03 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.88 | 4.75 | 0.12 | -0.297 | 12 | quality (higher is better) |
| technician | 4.88 | 4.75 | 0.12 | -0.043 | 12 | quality (higher is better) |
| skeptic | 8.12 | 7.44 | 0.69 | 0.412 | 12 | severity (lower is better) |
| risk_manager | 4.88 | 4.31 | 0.56 | 0.184 | 12 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 8 | 2 | 3 | 4 | 1 | 37.5 | 19.89 |
| 70-100 | 2 | 2 | 0 | 0 | 2 | 0.0 | -9.77 |


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
| run_20261005T133712Z | 2026-10-05T13:37:12+00:00 | yes | 1 | 1 | 0.0 |
| run_20261005T105502Z | 2026-10-05T10:55:02+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T094707Z | 2026-10-05T09:47:07+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T093900Z | 2026-10-05T09:39:00+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T074121Z | 2026-10-05T07:41:21+00:00 | no | 0 | 0 | 0.0 |

