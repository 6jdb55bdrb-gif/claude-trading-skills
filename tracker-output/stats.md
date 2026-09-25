# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 2 / unreviewed 3 · TAKE/SKIP 0/2 (0.0% TAKE)

**Portfolio:** $1,071.46 (+7.15% on $1,000.00) · 50.0% allocated · cash $500.00

**Total PnL:** +14.29% — equal weight across all 5 priced call(s)

**Generated:** 2026-09-25T17:13:21+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 5 |
| Reviewed calls | 2 |
| UNREVIEWED calls | 3 |
| Voided (not executable) | 1 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 2 |
| Open | 5 |
| Right | 3 |
| Wrong | 0 |
| Neutral | 2 |
| Hit rate % | 60.0 |
| **Total PnL % (equal weight, all calls)** | +14.29% |
| Average PnL % per call | 14.29 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** SDEV (long, squeeze, shadow) +47.12% — entry 1.04 → 1.5299999713897705
**Worst call:** GDC (long, squeeze, shadow) -22.73% — entry 1.76 → 1.3600000143051147

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 1 | 0 | 1 | 50.0 | 12.19 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 5 | 5 | 3 | 0 | 2 | 60.0 | 14.29 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 5 | 5 | 3 | 0 | 2 | 60.0 | 14.29 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 2 | 2 | 1 | 0 | 1 | 50.0 | 12.19 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 2 | quality (higher is better) |
| technician | 6.0 | 6.0 | 0.0 | — | 2 | quality (higher is better) |
| skeptic | 9.0 | 4.5 | 4.5 | — | 2 | severity (lower is better) |
| risk_manager | 8.0 | 5.0 | 3.0 | — | 2 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 0 | 0 | 0 | 0 | 0 | — | — |
| 40-70 | 2 | 2 | 1 | 0 | 1 | 50.0 | 12.19 |
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
| run_20260925T171257Z | 2026-09-25T17:12:57+00:00 | yes | — | — | — |
| run_20260925T142702Z | 2026-09-25T14:27:02+00:00 | yes | 0 | 0 | 0.0 |
| run_20260925T130426Z | 2026-09-25T13:04:26+00:00 | yes | 0 | 0 | 0.0 |
| run_20260925T104125Z | 2026-09-25T10:41:25+00:00 | yes | 0 | 0 | 0.0 |
| run_20260925T102701Z | 2026-09-25T10:27:01+00:00 | yes | 0 | 0 | 0.0 |

