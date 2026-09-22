# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 3 / unreviewed 1 · TAKE/SKIP 0/3 (0.0% TAKE)

**Generated:** 2026-09-22T08:50:48+00:00  
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
| Right | 1 |
| Wrong | 0 |
| Neutral | 3 |
| Hit rate % | 25.0 |
| Average PnL % per call | -3.39 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** NCPL (short, squeeze, shadow) +7.34% — entry 1.09 → 1.0099999904632568
**Worst call:** GDC (long, squeeze, shadow) -17.05% — entry 1.76 → 1.4600000381469727

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 3 | 3 | 0 | 0 | 3 | 0.0 | -6.96 |
| put | 1 | 1 | 1 | 0 | 0 | 100.0 | 7.34 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 4 | 4 | 1 | 0 | 3 | 25.0 | -3.39 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 4 | 4 | 1 | 0 | 3 | 25.0 | -3.39 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 1 | 0 | 2 | 33.3 | -4.52 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 3 | quality (higher is better) |
| technician | 2.0 | 6.0 | -4.0 | -0.841 | 3 | quality (higher is better) |
| skeptic | 10.0 | 6.75 | 3.25 | 0.954 | 3 | severity (lower is better) |
| risk_manager | 5.5 | 6.5 | -1.0 | 0.202 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 1 | 0 | 0 | 100.0 | 7.34 |
| 40-70 | 2 | 2 | 0 | 0 | 2 | 0.0 | -10.45 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260922T085025Z | 2026-09-22T08:50:25+00:00 | yes | — | — | — |
| run_20260921T194541Z | 2026-09-21T19:45:41+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T191256Z | 2026-09-21T19:12:56+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T181219Z | 2026-09-21T18:12:19+00:00 | yes | 1 | 0 | 0.0 |
| run_20260921T154146Z | 2026-09-21T15:41:46+00:00 | yes | 0 | 0 | 0.0 |

