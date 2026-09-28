# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 5 / unreviewed 0 · TAKE/SKIP 0/5 (0.0% TAKE)

**Portfolio:** $1,048.96 (+4.90% on $1,000.00) · 50.0% allocated · cash $500.00

**Total PnL:** +9.79% — equal weight across all 5 priced call(s)

**Generated:** 2026-09-28T09:13:29+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 5 |
| Reviewed calls | 5 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 1 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 5 |
| Open | 5 |
| Right | 3 |
| Wrong | 0 |
| Neutral | 2 |
| Hit rate % | 60.0 |
| **Total PnL % (equal weight, all calls)** | +9.79% |
| Average PnL % per call | 9.79 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +43.27% — entry 1.04 → 1.4900000095367432
**Worst call:** GDC (long, squeeze, shadow) -22.73% — entry 1.76 → 1.3600000143051147

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 5 | 5 | 3 | 0 | 2 | 60.0 | 9.79 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 5 | 5 | 3 | 0 | 2 | 60.0 | 9.79 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 5 | 5 | 3 | 0 | 2 | 60.0 | 9.79 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 5 | 5 | 3 | 0 | 2 | 60.0 | 9.79 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.67 | 5.75 | -1.08 | 0.093 | 5 | quality (higher is better) |
| technician | 4.67 | 5.5 | -0.83 | -0.199 | 5 | quality (higher is better) |
| skeptic | 8.67 | 5.75 | 2.92 | 0.758 | 5 | severity (lower is better) |
| risk_manager | 5.67 | 5.5 | 0.17 | 0.424 | 5 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 1 | 0 | 0 | 100.0 | 7.09 |
| 40-70 | 4 | 4 | 2 | 0 | 2 | 50.0 | 10.47 |
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
| run_20260928T091305Z | 2026-09-28T09:13:05+00:00 | yes | — | — | — |
| run_20260928T085559Z | 2026-09-28T08:55:59+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T072854Z | 2026-09-28T07:28:54+00:00 | no | 0 | 0 | 0.0 |
| run_20260927T182720Z | 2026-09-27T18:27:20+00:00 | no | 0 | 0 | 0.0 |
| run_20260926T082415Z | 2026-09-26T08:24:15+00:00 | no | 0 | 0 | 0.0 |

