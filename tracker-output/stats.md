# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 6 / unreviewed 0 · TAKE/SKIP 0/6 (0.0% TAKE)

**Portfolio:** $999.58 (-0.04% on $1,000.00) · 60.0% allocated · cash $400.00

**Total PnL:** -0.07% — equal weight across all 6 priced call(s)

**Generated:** 2026-09-28T15:55:40+00:00  
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
| Open | 6 |
| Right | 3 |
| Wrong | 0 |
| Neutral | 3 |
| Hit rate % | 50.0 |
| **Total PnL % (equal weight, all calls)** | -0.07% |
| Average PnL % per call | -0.07 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +43.29% — entry 1.04 → 1.4902000427246094
**Worst call:** GDC (long, squeeze, shadow) -26.14% — entry 1.76 → 1.2999999523162842

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 6 | 6 | 3 | 0 | 3 | 50.0 | -0.07 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 6 | 6 | 3 | 0 | 3 | 50.0 | -0.07 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 6 | 6 | 3 | 0 | 3 | 50.0 | -0.07 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 6 | 6 | 3 | 0 | 3 | 50.0 | -0.07 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 6.0 | 4.5 | 1.5 | 0.078 | 6 | quality (higher is better) |
| technician | 4.67 | 5.0 | -0.33 | 0.146 | 6 | quality (higher is better) |
| skeptic | 8.33 | 6.83 | 1.5 | 0.666 | 6 | severity (lower is better) |
| risk_manager | 5.33 | 5.0 | 0.33 | 0.564 | 6 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 0 | 0 | 1 | 0.0 | -12.2 |
| 40-70 | 5 | 5 | 3 | 0 | 2 | 60.0 | 2.36 |
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
| run_20260928T155514Z | 2026-09-28T15:55:14+00:00 | yes | — | — | — |
| run_20260928T140429Z | 2026-09-28T14:04:29+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T140229Z | 2026-09-28T14:02:29+00:00 | yes | 1 | 0 | 0.0 |
| run_20260928T091305Z | 2026-09-28T09:13:05+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T085559Z | 2026-09-28T08:55:59+00:00 | yes | 0 | 0 | 0.0 |

