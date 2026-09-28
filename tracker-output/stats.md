# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 6 / unreviewed 0 · TAKE/SKIP 0/6 (0.0% TAKE)

**Portfolio:** $1,009.12 (+0.91% on $1,000.00) · 60.0% allocated · cash $400.00

**Total PnL:** +1.52% — equal weight across all 6 priced call(s)

**Generated:** 2026-09-28T16:30:19+00:00  
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
| **Total PnL % (equal weight, all calls)** | +1.52% |
| Average PnL % per call | 1.52 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +45.19% — entry 1.04 → 1.5099999904632568
**Worst call:** GDC (long, squeeze, shadow) -25.57% — entry 1.76 → 1.309999942779541

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 6 | 6 | 3 | 0 | 3 | 50.0 | 1.52 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 6 | 6 | 3 | 0 | 3 | 50.0 | 1.52 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 6 | 6 | 3 | 0 | 3 | 50.0 | 1.52 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 6 | 6 | 3 | 0 | 3 | 50.0 | 1.52 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 6.0 | 4.5 | 1.5 | 0.123 | 6 | quality (higher is better) |
| technician | 4.67 | 5.0 | -0.33 | 0.147 | 6 | quality (higher is better) |
| skeptic | 8.33 | 6.83 | 1.5 | 0.652 | 6 | severity (lower is better) |
| risk_manager | 5.33 | 5.0 | 0.33 | 0.551 | 6 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 0 | 0 | 1 | 0.0 | -13.41 |
| 40-70 | 5 | 5 | 3 | 0 | 2 | 60.0 | 4.51 |
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
| run_20260928T162954Z | 2026-09-28T16:29:54+00:00 | yes | — | — | — |
| run_20260928T155514Z | 2026-09-28T15:55:14+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T140429Z | 2026-09-28T14:04:29+00:00 | yes | 0 | 0 | 0.0 |
| run_20260928T140229Z | 2026-09-28T14:02:29+00:00 | yes | 1 | 0 | 0.0 |
| run_20260928T091305Z | 2026-09-28T09:13:05+00:00 | yes | 0 | 0 | 0.0 |

