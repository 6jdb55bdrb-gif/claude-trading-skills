# Lowcap Call Tracker — Statistics

**Generated:** 2026-09-21T19:46:05+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 3 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 3 |
| Open | 3 |
| Right | 1 |
| Wrong | 0 |
| Neutral | 2 |
| Hit rate % | 33.3 |
| Average PnL % per call | -7.92 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** NCPL (short, squeeze, shadow) +0.90% — entry 1.09 → 1.080199956893921
**Worst call:** GDC (long, squeeze, shadow) -18.18% — entry 1.76 → 1.440000057220459

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 0 | 0 | 2 | 0.0 | -12.34 |
| put | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.9 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 3 | 3 | 1 | 0 | 2 | 33.3 | -7.92 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 3 | 3 | 1 | 0 | 2 | 33.3 | -7.92 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 1 | 0 | 2 | 33.3 | -7.92 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.5 | 0.0 | — | 3 | quality (higher is better) |
| technician | 2.0 | 6.0 | -4.0 | -0.794 | 3 | quality (higher is better) |
| skeptic | 10.0 | 6.75 | 3.25 | 0.975 | 3 | severity (lower is better) |
| risk_manager | 5.5 | 6.5 | -1.0 | 0.282 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.9 |
| 40-70 | 2 | 2 | 0 | 0 | 2 | 0.0 | -12.34 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260921T194541Z | 2026-09-21T19:45:41+00:00 | yes | — | — | — |
| run_20260921T191256Z | 2026-09-21T19:12:56+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T181219Z | 2026-09-21T18:12:19+00:00 | yes | 1 | 0 | 0.0 |
| run_20260921T154146Z | 2026-09-21T15:41:46+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T152217Z | 2026-09-21T15:22:17+00:00 | yes | 1 | 0 | 0.0 |

