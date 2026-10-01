# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: None.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 8 / unreviewed 0 · TAKE/SKIP 1/7 (12.5% TAKE)

**Portfolio:** $1,117.48 (+11.75% on $1,000.00) · 20.0% allocated · cash $917.48

**Total PnL:** +14.68% — equal weight across all 8 priced call(s)

**Generated:** 2026-10-01T13:11:55+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 8 |
| Reviewed calls | 8 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 1 |
| Shadow (SKIP) calls | 7 |
| Open | 2 |
| Right | 2 |
| Wrong | 4 |
| Neutral | 2 |
| Hit rate % | 25.0 |
| **Total PnL % (equal weight, all calls)** | +14.68% |
| Average PnL % per call | 14.68 |
| Portfolio PnL % (equal weight, TAKE only) | 0.0 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 8 | 2 | 2 | 4 | 2 | 25.0 | 14.68 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 8 | 2 | 2 | 4 | 2 | 25.0 | 14.68 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 8 | 2 | 2 | 4 | 2 | 25.0 | 14.68 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 1 | 1 | 0 | 0 | 1 | 0.0 | 0.0 |
| SKIP (shadow) | 7 | 1 | 2 | 4 | 1 | 28.6 | 16.78 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -16.78 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 6.0 | 4.67 | 1.33 | -0.044 | 8 | quality (higher is better) |
| technician | 5.0 | 4.5 | 0.5 | 0.328 | 8 | quality (higher is better) |
| skeptic | 8.5 | 7.58 | 0.92 | 0.367 | 8 | severity (lower is better) |
| risk_manager | 6.5 | 4.17 | 2.33 | 0.694 | 8 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 1 | 0 | 1 | 1 | 0.0 | -7.09 |
| 40-70 | 6 | 1 | 2 | 3 | 1 | 33.3 | 21.94 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |


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
| run_20261001T125611Z | 2026-10-01T12:56:11+00:00 | yes | 1 | 1 | 0.0 |
| run_20261001T102109Z | 2026-10-01T10:21:09+00:00 | yes | 0 | 0 | 0.0 |
| run_20261001T101832Z | 2026-10-01T10:18:32+00:00 | yes | 2 | 0 | 0.0 |
| run_20261001T075438Z | 2026-10-01T07:54:39+00:00 | no | 0 | 0 | 0.0 |
| run_20260930T191539Z | 2026-09-30T19:15:39+00:00 | yes | 0 | 0 | 0.0 |

