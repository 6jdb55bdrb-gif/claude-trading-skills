# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 2 / unreviewed 3 · TAKE/SKIP 0/2 (0.0% TAKE)

**Total PnL:** +6.91% — equal weight across all 5 priced call(s)

**Generated:** 2026-09-25T10:41:48+00:00  
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
| Right | 2 |
| Wrong | 0 |
| Neutral | 3 |
| Hit rate % | 40.0 |
| **Total PnL % (equal weight, all calls)** | +6.91% |
| Average PnL % per call | 6.91 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** GRML (long, squeeze, unreviewed) +39.55% — entry 10.67 → 14.890000343322754
**Worst call:** GDC (long, squeeze, shadow) -18.18% — entry 1.76 → 1.440000057220459

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 1 | 0 | 1 | 50.0 | 2.93 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 5 | 5 | 2 | 0 | 3 | 40.0 | 6.91 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 5 | 5 | 2 | 0 | 3 | 40.0 | 6.91 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 2 | 2 | 1 | 0 | 1 | 50.0 | 2.93 |

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
| 40-70 | 2 | 2 | 1 | 0 | 1 | 50.0 | 2.93 |
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
| run_20260925T104125Z | 2026-09-25T10:41:25+00:00 | yes | — | — | — |
| run_20260925T102701Z | 2026-09-25T10:27:01+00:00 | yes | 0 | 0 | 0.0 |
| run_20260925T071142Z | 2026-09-25T07:11:42+00:00 | no | 0 | 0 | 0.0 |
| run_20260924T202735Z | 2026-09-24T20:27:35+00:00 | yes | 1 | 0 | 0.0 |
| run_20260924T193032Z | 2026-09-24T19:30:32+00:00 | yes | 0 | 0 | 0.0 |

