# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 6 / unreviewed 0 · TAKE/SKIP 0/6 (0.0% TAKE)

**Portfolio:** $1,121.48 (+12.15% on $1,000.00) · 10.0% allocated · cash $841.66

**Total PnL:** +20.25% — equal weight across all 6 priced call(s)

**Generated:** 2026-09-30T15:07:28+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 6 |
| Reviewed calls | 6 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 1 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 6 |
| Open | 1 |
| Right | 2 |
| Wrong | 4 |
| Neutral | 0 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +20.25% |
| Average PnL % per call | 20.25 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +179.82% — entry 1.04 → 2.910099983215332
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 6 | 1 | 2 | 4 | 0 | 33.3 | 20.25 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 6 | 1 | 2 | 4 | 0 | 33.3 | 20.25 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 6 | 1 | 2 | 4 | 0 | 33.3 | 20.25 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 6 | 1 | 2 | 4 | 0 | 33.3 | 20.25 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 6.0 | 4.88 | 1.12 | -0.103 | 6 | quality (higher is better) |
| technician | 5.0 | 4.75 | 0.25 | 0.499 | 6 | quality (higher is better) |
| skeptic | 8.5 | 7.12 | 1.38 | 0.479 | 6 | severity (lower is better) |
| risk_manager | 6.5 | 4.5 | 2.0 | 0.808 | 6 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 0 | 0 | 1 | 0 | 0.0 | -14.17 |
| 40-70 | 5 | 1 | 2 | 3 | 0 | 40.0 | 27.13 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |


### Voided calls

Kept for the record, excluded from every figure above: these
could not have been executed, so they cannot have made or lost
anything.

| Ticker | Instrument | PnL % | Reason |
|---|---|---|---|
| NCPL | put | -27.06% | put: not executable — no listed options and no borrow on this name |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260930T150659Z | 2026-09-30T15:06:59+00:00 | yes | — | — | — |
| run_20260930T130227Z | 2026-09-30T13:02:28+00:00 | yes | 0 | 0 | 0.0 |
| run_20260929T193738Z | 2026-09-29T19:37:38+00:00 | yes | 0 | 0 | 0.0 |
| run_20260929T172853Z | 2026-09-29T17:28:53+00:00 | yes | 0 | 0 | 0.0 |
| run_20260929T143950Z | 2026-09-29T14:39:50+00:00 | yes | 0 | 0 | 0.0 |

