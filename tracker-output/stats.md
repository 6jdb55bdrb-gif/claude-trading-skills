# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 3 / unreviewed 2 · TAKE/SKIP 0/3 (0.0% TAKE)

**Generated:** 2026-09-23T14:24:21+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 5 |
| Reviewed calls | 3 |
| UNREVIEWED calls | 2 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 3 |
| Open | 5 |
| Right | 2 |
| Wrong | 0 |
| Neutral | 3 |
| Hit rate % | 40.0 |
| Average PnL % per call | 4.24 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** GRML (long, squeeze, unreviewed) +25.01% — entry 10.67 → 13.338800430297852
**Worst call:** NCPL (short, squeeze, shadow) -13.76% — entry 1.09 → 1.2400000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 1 | 0 | 1 | 50.0 | 4.97 |
| put | 1 | 1 | 0 | 0 | 1 | 0.0 | -13.76 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 5 | 5 | 2 | 0 | 3 | 40.0 | 4.24 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 5 | 5 | 2 | 0 | 3 | 40.0 | 4.24 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 1 | 0 | 2 | 33.3 | -1.27 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 3 | quality (higher is better) |
| technician | 6.0 | 4.0 | 2.0 | 0.821 | 3 | quality (higher is better) |
| skeptic | 9.0 | 7.25 | 1.75 | -0.087 | 3 | severity (lower is better) |
| risk_manager | 8.0 | 5.25 | 2.75 | 0.828 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 0 | 0 | 1 | 0.0 | -13.76 |
| 40-70 | 2 | 2 | 1 | 0 | 1 | 50.0 | 4.97 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260923T142356Z | 2026-09-23T14:23:56+00:00 | yes | — | — | — |
| run_20260923T102122Z | 2026-09-23T10:21:22+00:00 | yes | 0 | 0 | 0.0 |
| run_20260923T052407Z | 2026-09-23T05:24:07+00:00 | no | 0 | 0 | 0.0 |
| run_20260923T052313Z | 2026-09-23T05:23:13+00:00 | no | 0 | 0 | 0.0 |
| run_20260923T051728Z | 2026-09-23T05:17:28+00:00 | yes | 0 | 0 | 0.0 |

