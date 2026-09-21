# Lowcap Call Tracker — Statistics

**Generated:** 2026-09-21T19:13:20+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 3 |
| TAKE calls | 0 |
| Shadow (SKIP) calls | 3 |
| Open | 3 |
| Right | 0 |
| Wrong | 0 |
| Neutral | 3 |
| Hit rate % | 0.0 |
| Average PnL % per call | -8.23 |
| Portfolio PnL % (equal weight, TAKE only) | — |

**Best call:** NCPL (short, squeeze, shadow) -2.75% — entry 1.09 → 1.1200000047683716
**Worst call:** GDC (long, squeeze, shadow) -15.90% — entry 1.76 → 1.4802000522613525

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 2 | 2 | 0 | 0 | 2 | 0.0 | -10.97 |
| put | 1 | 1 | 0 | 0 | 1 | 0.0 | -2.75 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 3 | 3 | 0 | 0 | 3 | 0.0 | -8.23 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 3 | 3 | 0 | 0 | 3 | 0.0 | -8.23 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 0 | 0 | 0 | 0 | 0 | — | — |
| SKIP (shadow) | 3 | 3 | 0 | 0 | 3 | 0.0 | -8.23 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** None → no comparison yet

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | — | 4.5 | — | — | 3 | quality (higher is better) |
| technician | — | 4.67 | — | -0.693 | 3 | quality (higher is better) |
| skeptic | — | 7.83 | — | 0.997 | 3 | severity (lower is better) |
| risk_manager | — | 6.17 | — | 0.423 | 3 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 1 | 1 | 0 | 0 | 1 | 0.0 | -2.75 |
| 40-70 | 2 | 2 | 0 | 0 | 2 | 0.0 | -10.97 |
| 70-100 | 0 | 0 | 0 | 0 | 0 | — | — |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20260921T191256Z | 2026-09-21T19:12:56+00:00 | yes | — | — | — |
| run_20260921T181219Z | 2026-09-21T18:12:19+00:00 | yes | 1 | 0 | 0.0 |
| run_20260921T154146Z | 2026-09-21T15:41:46+00:00 | yes | 0 | 0 | 0.0 |
| run_20260921T152217Z | 2026-09-21T15:22:17+00:00 | yes | 1 | 0 | 0.0 |
| run_20260921T103635Z | 2026-09-21T10:36:35+00:00 | yes | 0 | 0 | 0.0 |

