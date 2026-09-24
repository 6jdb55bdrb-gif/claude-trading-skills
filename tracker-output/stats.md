# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: ANTHROPIC_API_KEY is not set.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 3 / unreviewed 2 · TAKE/SKIP 0/3 (0.0% TAKE)

**Total PnL:** +0.01% — equal weight across all 5 priced call(s)

**Generated:** 2026-09-24T16:59:06+00:00  
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
| **Total PnL % (equal weight, all calls)** | +0.01% |
| Average PnL % per call | 0.01 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** GRML (long, squeeze, unreviewed) +42.08% — entry 10.67 → 15.15999984741211
**Worst call:** NCPL (short, squeeze, shadow) -40.83% — entry 1.09 → 1.534999966621399

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 1 | 0 | 1 | 50.0 | 4.2 |
| put | 1 | 1 | 0 | 0 | 1 | 0.0 | -40.83 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 5 | 5 | 2 | 0 | 3 | 40.0 | 0.01 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 5 | 5 | 2 | 0 | 3 | 40.0 | 0.01 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 1 | 0 | 2 | 33.3 | -10.81 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 3 | quality (higher is better) |
| technician | 6.0 | 4.0 | 2.0 | 0.795 | 3 | quality (higher is better) |
| skeptic | 9.0 | 7.25 | 1.75 | -0.044 | 3 | severity (lower is better) |
| risk_manager | 8.0 | 5.25 | 2.75 | 0.852 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 0 | 0 | 1 | 0.0 | -40.83 |
| 40-70 | 2 | 2 | 1 | 0 | 1 | 50.0 | 4.2 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260924T165842Z | 2026-09-24T16:58:42+00:00 | yes | — | — | — |
| run_20260924T152058Z | 2026-09-24T15:20:58+00:00 | yes | 0 | 0 | 0.0 |
| run_20260924T123112Z | 2026-09-24T12:31:12+00:00 | yes | 0 | 0 | 0.0 |
| run_20260924T103453Z | 2026-09-24T10:34:53+00:00 | yes | 0 | 0 | 0.0 |
| run_20260924T080257Z | 2026-09-24T08:02:57+00:00 | yes | 0 | 0 | 0.0 |

