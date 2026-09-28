# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 6 / unreviewed 0 · TAKE/SKIP 0/6 (0.0% TAKE)

**Portfolio:** $1,033.42 (+3.34% on $1,000.00) · 60.0% allocated · cash $400.00

**Total PnL:** +5.57% — equal weight across all 6 priced call(s)

**Generated:** 2026-09-28T14:04:52+00:00  
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
| Right | 2 |
| Wrong | 0 |
| Neutral | 4 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +5.57% |
| Average PnL % per call | 5.57 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +60.56% — entry 1.04 → 1.669800043106079
**Worst call:** GDC (long, squeeze, shadow) -23.86% — entry 1.76 → 1.340000033378601

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 6 | 6 | 2 | 0 | 4 | 33.3 | 5.57 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 6 | 6 | 2 | 0 | 4 | 33.3 | 5.57 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 6 | 6 | 2 | 0 | 4 | 33.3 | 5.57 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 6 | 6 | 2 | 0 | 4 | 33.3 | 5.57 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 6.0 | 4.88 | 1.12 | 0.063 | 6 | quality (higher is better) |
| technician | 5.0 | 4.75 | 0.25 | 0.214 | 6 | quality (higher is better) |
| skeptic | 8.5 | 7.12 | 1.38 | 0.633 | 6 | severity (lower is better) |
| risk_manager | 6.5 | 4.5 | 2.0 | 0.651 | 6 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 0 | 0 | 1 | 0.0 | -8.65 |
| 40-70 | 5 | 5 | 2 | 0 | 3 | 40.0 | 8.41 |
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
| run_20260928T140429Z | 2026-09-28T14:04:29+00:00 | yes | — | — | — |
| run_20260928T140229Z | 2026-09-28T14:02:29+00:00 | yes | 1 | 0 | 0.0 |
| run_20260928T091305Z | 2026-09-28T09:13:05+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T085559Z | 2026-09-28T08:55:59+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T072854Z | 2026-09-28T07:28:54+00:00 | no | 0 | 0 | 0.0 |

