# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: None.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 10 / unreviewed 0 · TAKE/SKIP 1/9 (10.0% TAKE)

**Portfolio:** $1,128.41 (+12.84% on $1,000.00) · 30.0% allocated · cash $798.49

**Total PnL:** +12.84% — equal weight across all 10 priced call(s)

**Generated:** 2026-10-01T14:26:34+00:00  
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
| Right | 4 |
| Wrong | 5 |
| Neutral | 1 |
| Hit rate % | 40.0 |
| **Total PnL % (equal weight, all calls)** | +12.84% |
| Average PnL % per call | 12.84 |
| Portfolio PnL % (equal weight, TAKE only) | -18.99 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 10 | 3 | 4 | 5 | 1 | 40.0 | 12.84 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 10 | 3 | 4 | 5 | 1 | 40.0 | 12.84 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 10 | 3 | 4 | 5 | 1 | 40.0 | 12.84 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 1 | 0 | 0 | 1 | 0 | 0.0 | -18.99 |
| SKIP (shadow) | 9 | 3 | 4 | 4 | 1 | 44.4 | 16.38 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -35.37 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.88 | 5.17 | -0.29 | -0.184 | 10 | quality (higher is better) |
| technician | 4.88 | 4.75 | 0.12 | 0.11 | 10 | quality (higher is better) |
| skeptic | 8.12 | 7.33 | 0.79 | 0.423 | 10 | severity (lower is better) |
| risk_manager | 4.88 | 4.25 | 0.62 | 0.567 | 10 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 1 | 1 | 1 | 0 | 50.0 | 9.24 |
| 40-70 | 7 | 1 | 3 | 4 | 0 | 42.9 | 16.54 |
| 70-100 | 1 | 1 | 0 | 0 | 1 | 0.0 | -5.86 |


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
| run_20261001T135115Z | 2026-10-01T13:51:15+00:00 | yes | 2 | 1 | 0.0 |
| run_20261001T125611Z | 2026-10-01T12:56:11+00:00 | yes | 1 | 1 | 0.0 |
| run_20261001T102109Z | 2026-10-01T10:21:09+00:00 | yes | 0 | 0 | 0.0 |
| run_20261001T101832Z | 2026-10-01T10:18:32+00:00 | yes | 2 | 0 | 0.0 |
| run_20261001T075438Z | 2026-10-01T07:54:39+00:00 | no | 0 | 0 | 0.0 |

