# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 3 / unreviewed 3 · TAKE/SKIP 0/3 (0.0% TAKE)

**Total PnL:** +1.24% — equal weight across all 6 priced call(s)

**Generated:** 2026-09-25T10:27:25+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 6 |
| Reviewed calls | 3 |
| UNREVIEWED calls | 3 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 3 |
| Open | 5 |
| Right | 2 |
| Wrong | 1 |
| Neutral | 3 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +1.24% |
| Average PnL % per call | 1.24 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** GRML (long, squeeze, unreviewed) +39.55% — entry 10.67 → 14.890000343322754
**Worst call:** NCPL (short, squeeze, shadow) -27.06% — entry 1.09 → 1.3849999904632568

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 1 | 0 | 1 | 50.0 | 2.93 |
| put | 1 | 0 | 0 | 1 | 0 | 0.0 | -27.06 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 6 | 5 | 2 | 1 | 3 | 33.3 | 1.24 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 6 | 5 | 2 | 1 | 3 | 33.3 | 1.24 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 2 | 1 | 1 | 1 | 33.3 | -7.07 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 3 | quality (higher is better) |
| technician | 6.0 | 4.0 | 2.0 | 0.634 | 3 | quality (higher is better) |
| skeptic | 9.0 | 7.25 | 1.75 | 0.188 | 3 | severity (lower is better) |
| risk_manager | 8.0 | 5.25 | 2.75 | 0.949 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 0 | 0 | 1 | 0 | 0.0 | -27.06 |
| 40-70 | 2 | 2 | 1 | 0 | 1 | 50.0 | 2.93 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260925T102701Z | 2026-09-25T10:27:01+00:00 | yes | — | — | — |
| run_20260925T071142Z | 2026-09-25T07:11:42+00:00 | no | 0 | 0 | 0.0 |
| run_20260924T202735Z | 2026-09-24T20:27:35+00:00 | yes | 1 | 0 | 0.0 |
| run_20260924T193032Z | 2026-09-24T19:30:32+00:00 | yes | 0 | 0 | 0.0 |
| run_20260924T165842Z | 2026-09-24T16:58:42+00:00 | yes | 0 | 0 | 0.0 |

