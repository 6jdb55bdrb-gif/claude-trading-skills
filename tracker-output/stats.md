# Lowcap Call Tracker — Statistics

**Backend:** UNKNOWN · reviewed 16 / unreviewed 0 · TAKE/SKIP 3/13 (18.8% TAKE)

**Account (every call):** $1,156.82 (+15.68% on $1,000.00) · 60.0% allocated · cash $582.77

**TAKE only (the Judge's scorecard):** $963.29 (-3.67%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +9.80% — equal weight across all 16 priced call(s)

**Generated:** 2026-10-08T05:49:44+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 16 |
| Reviewed calls | 16 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 3 |
| Shadow (SKIP) calls | 13 |
| Open | 6 |
| Right | 6 |
| Wrong | 7 |
| Neutral | 3 |
| Hit rate % | 37.5 |
| **Total PnL % (equal weight, all calls)** | +9.80% |
| Average PnL % per call | 9.8 |
| Portfolio PnL % (equal weight, TAKE only) | -12.24 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -38.07% — entry 4.57 → 2.83

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 16 | 6 | 6 | 7 | 3 | 37.5 | 9.8 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.13 |
| stock | 15 | 5 | 5 | 7 | 3 | 33.3 | 10.44 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.13 |
| squeeze | 15 | 5 | 5 | 7 | 3 | 33.3 | 10.44 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 3 | 1 | 0 | 2 | 1 | 0.0 | -12.24 |
| SKIP (shadow) | 13 | 5 | 6 | 5 | 2 | 46.2 | 14.89 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -27.12 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.4 | 0.1 | -0.111 | 16 | quality (higher is better) |
| technician | 4.42 | 4.9 | -0.48 | 0.002 | 16 | quality (higher is better) |
| skeptic | 7.75 | 7.1 | 0.65 | 0.238 | 16 | severity (lower is better) |
| risk_manager | 4.75 | 4.45 | 0.3 | 0.248 | 16 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 10 | 3 | 4 | 5 | 1 | 40.0 | 14.17 |
| 70-100 | 4 | 3 | 1 | 1 | 2 | 25.0 | -26.91 |


### Voided calls

Kept for the record, excluded from every figure above: these
could not have been executed, so they cannot have made or lost
anything.

| Ticker | Instrument | PnL % | Reason |
|---|---|---|---|
| NCPL | put | -27.06% | put: not executable — no listed options and no borrow on this name |
| SDEV | — | +0.00% | duplicate: created only because call 8 was falsely stopped on a pre-entry bar |

### Recent runs

| Run | Started | Screened | New calls | Closed | LLM $ |
|---|---|---|---|---|---|
| run_20261008T054608Z | 2026-10-08T05:46:08+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T054557Z | 2026-10-08T05:45:58+00:00 | no | 0 | 0 | 0.0 |
| run_20261007T200450Z | 2026-10-07T20:04:50+00:00 | yes | 2 | 1 | 0.0 |
| run_20261007T171621Z | 2026-10-07T17:16:21+00:00 | yes | 0 | 0 | 0.0 |
| run_20261007T144502Z | 2026-10-07T14:45:02+00:00 | yes | 0 | 0 | 0.0 |
