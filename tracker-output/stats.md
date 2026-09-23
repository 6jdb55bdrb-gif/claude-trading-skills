# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 3 / unreviewed 1 · TAKE/SKIP 0/3 (0.0% TAKE)

**Generated:** 2026-09-23T10:21:46+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 4 |
| Reviewed calls | 3 |
| UNREVIEWED calls | 1 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 3 |
| Open | 4 |
| Right | 3 |
| Wrong | 0 |
| Neutral | 1 |
| Hit rate % | 75.0 |
| Average PnL % per call | 14.13 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** GRML (long, squeeze, unreviewed) +33.08% — entry 10.67 → 14.199999809265137
**Worst call:** GDC (long, squeeze, shadow) -6.82% — entry 1.76 → 1.6399999856948853

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 1 | 0 | 1 | 50.0 | 4.76 |
| put | 1 | 1 | 1 | 0 | 0 | 100.0 | 13.92 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 4 | 4 | 3 | 0 | 1 | 75.0 | 14.13 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 4 | 4 | 3 | 0 | 1 | 75.0 | 14.13 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 2 | 0 | 1 | 66.7 | 7.82 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 3 | quality (higher is better) |
| technician | 4.0 | 6.0 | -2.0 | -0.415 | 3 | quality (higher is better) |
| skeptic | 9.5 | 4.5 | 5.0 | 0.965 | 3 | severity (lower is better) |
| risk_manager | 6.75 | 5.0 | 1.75 | 0.7 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 1 | 0 | 0 | 100.0 | 13.92 |
| 40-70 | 2 | 2 | 1 | 0 | 1 | 50.0 | 4.76 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260923T102122Z | 2026-09-23T10:21:22+00:00 | yes | — | — | — |
| run_20260923T052407Z | 2026-09-23T05:24:07+00:00 | no | 0 | 0 | 0.0 |
| run_20260923T052313Z | 2026-09-23T05:23:13+00:00 | no | 0 | 0 | 0.0 |
| run_20260923T051728Z | 2026-09-23T05:17:28+00:00 | yes | 0 | 0 | 0.0 |
| run_20260923T051333Z | 2026-09-23T05:13:33+00:00 | yes | 0 | 0 | 0.0 |

