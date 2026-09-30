# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 6 / unreviewed 0 · TAKE/SKIP 0/6 (0.0% TAKE)

**Portfolio:** $1,165.00 (+16.50% on $1,000.00) · 20.0% allocated · cash $756.72

**Total PnL:** +27.50% — equal weight across all 6 priced call(s)

**Generated:** 2026-09-30T13:02:53+00:00  
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
| Open | 2 |
| Right | 2 |
| Wrong | 3 |
| Neutral | 1 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +27.50% |
| Average PnL % per call | 27.5 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +214.42% — entry 1.04 → 3.2699999809265137
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 6 | 2 | 2 | 3 | 1 | 33.3 | 27.5 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 6 | 2 | 2 | 3 | 1 | 33.3 | 27.5 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 6 | 2 | 2 | 3 | 1 | 33.3 | 27.5 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 6 | 2 | 2 | 3 | 1 | 33.3 | 27.5 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 6.0 | 4.88 | 1.12 | -0.109 | 6 | quality (higher is better) |
| technician | 5.0 | 4.75 | 0.25 | 0.5 | 6 | quality (higher is better) |
| skeptic | 8.5 | 7.12 | 1.38 | 0.478 | 6 | severity (lower is better) |
| risk_manager | 6.5 | 4.5 | 2.0 | 0.791 | 6 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 0 | 0 | 1 | 0 | 0.0 | -14.17 |
| 40-70 | 5 | 2 | 2 | 2 | 1 | 40.0 | 35.83 |
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
| run_20260930T130227Z | 2026-09-30T13:02:28+00:00 | yes | — | — | — |
| run_20260929T193738Z | 2026-09-29T19:37:38+00:00 | yes | 0 | 0 | 0.0 |
| run_20260929T172853Z | 2026-09-29T17:28:53+00:00 | yes | 0 | 0 | 0.0 |
| run_20260929T143950Z | 2026-09-29T14:39:50+00:00 | yes | 0 | 0 | 0.0 |
| run_20260929T125313Z | 2026-09-29T12:53:13+00:00 | yes | 0 | 0 | 0.0 |

