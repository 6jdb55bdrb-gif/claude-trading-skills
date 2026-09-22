# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 3 / unreviewed 1 · TAKE/SKIP 0/3 (0.0% TAKE)

**Generated:** 2026-09-22T15:09:33+00:00  
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
| Right | 4 |
| Wrong | 0 |
| Neutral | 0 |
| Hit rate % | 100.0 |
| Average PnL % per call | 18.14 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** GRML (long, squeeze, unreviewed) +47.71% — entry 10.67 → 15.76099967956543
**Worst call:** SDEV (long, squeeze, shadow) +2.88% — entry 1.04 → 1.0700000524520874

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 3 | 3 | 3 | 0 | 0 | 100.0 | 20.46 |
| put | 1 | 1 | 1 | 0 | 0 | 100.0 | 11.17 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 4 | 4 | 4 | 0 | 0 | 100.0 | 18.14 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 4 | 4 | 4 | 0 | 0 | 100.0 | 18.14 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 3 | 0 | 0 | 100.0 | 8.28 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | — | — | — | 3 | quality (higher is better) |
| technician | 4.67 | — | — | -0.535 | 3 | quality (higher is better) |
| skeptic | 7.83 | — | — | -0.307 | 3 | severity (lower is better) |
| risk_manager | 6.17 | — | — | -0.981 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 1 | 0 | 0 | 100.0 | 11.17 |
| 40-70 | 2 | 2 | 2 | 0 | 0 | 100.0 | 6.84 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260922T150906Z | 2026-09-22T15:09:06+00:00 | yes | — | — | — |
| run_20260922T085025Z | 2026-09-22T08:50:25+00:00 | yes | 1 | 0 | 0.0 |
| run_20260921T194541Z | 2026-09-21T19:45:41+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T191256Z | 2026-09-21T19:12:56+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T181219Z | 2026-09-21T18:12:19+00:00 | yes | 1 | 0 | 0.0 |

