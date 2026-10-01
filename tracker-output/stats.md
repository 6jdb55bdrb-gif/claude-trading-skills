# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 10 / unreviewed 0 · TAKE/SKIP 1/9 (10.0% TAKE)

**Portfolio:** $1,114.08 (+11.41% on $1,000.00) · 30.0% allocated · cash $798.49

**Total PnL:** +11.41% — equal weight across all 10 priced call(s)

**Generated:** 2026-10-01T15:00:44+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 10 |
| Reviewed calls | 10 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 1 |
| Shadow (SKIP) calls | 9 |
| Open | 3 |
| Right | 3 |
| Wrong | 5 |
| Neutral | 2 |
| Hit rate % | 30.0 |
| **Total PnL % (equal weight, all calls)** | +11.41% |
| Average PnL % per call | 11.41 |
| Portfolio PnL % (equal weight, TAKE only) | -18.99 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 10 | 3 | 3 | 5 | 2 | 30.0 | 11.41 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 10 | 3 | 3 | 5 | 2 | 30.0 | 11.41 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 10 | 3 | 3 | 5 | 2 | 30.0 | 11.41 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 1 | 0 | 0 | 1 | 0 | 0.0 | -18.99 |
| SKIP (shadow) | 9 | 3 | 3 | 4 | 2 | 33.3 | 14.79 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -33.78 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.33 | 5.36 | -1.02 | -0.169 | 10 | quality (higher is better) |
| technician | 4.0 | 5.14 | -1.14 | 0.115 | 10 | quality (higher is better) |
| skeptic | 9.0 | 7.07 | 1.93 | 0.419 | 10 | severity (lower is better) |
| risk_manager | 5.0 | 4.29 | 0.71 | 0.588 | 10 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 1 | 1 | 1 | 0 | 50.0 | 6.46 |
| 40-70 | 7 | 1 | 2 | 4 | 1 | 28.6 | 15.71 |
| 70-100 | 1 | 1 | 0 | 0 | 1 | 0.0 | -8.84 |


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
| run_20261001T150019Z | 2026-10-01T15:00:19+00:00 | yes | — | — | — |
| run_20261001T143713Z | 2026-10-01T14:37:13+00:00 | yes | 0 | 0 | 0.0 |
| run_20261001T135115Z | 2026-10-01T13:51:15+00:00 | yes | 2 | 1 | 0.0 |
| run_20261001T125611Z | 2026-10-01T12:56:11+00:00 | yes | 1 | 1 | 0.0 |
| run_20261001T102109Z | 2026-10-01T10:21:09+00:00 | yes | 0 | 0 | 0.0 |

