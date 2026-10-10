# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 22 / unreviewed 0 · TAKE/SKIP 5/17 (22.7% TAKE)

**Account (every call):** $1,138.23 (+13.82% on $1,000.00) · 100.0% allocated · cash $100.47

**TAKE only (the Judge's scorecard):** $981.02 (-1.90%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +6.28% — equal weight across all 22 priced call(s)

**Generated:** 2026-10-10T09:39:03+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 22 |
| Reviewed calls | 22 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 17 |
| Open | 10 |
| Right | 9 |
| Wrong | 9 |
| Neutral | 4 |
| Hit rate % | 40.9 |
| **Total PnL % (equal weight, all calls)** | +6.28% |
| Average PnL % per call | 6.28 |
| Portfolio PnL % (equal weight, TAKE only) | -3.8 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 22 | 10 | 9 | 9 | 4 | 40.9 | 6.28 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.27 |
| stock | 21 | 9 | 8 | 9 | 4 | 38.1 | 6.57 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.27 |
| premarket_gap | 1 | 1 | 0 | 0 | 1 | 0.0 | -4.44 |
| squeeze | 20 | 8 | 8 | 9 | 3 | 40.0 | 7.12 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -3.8 |
| SKIP (shadow) | 17 | 7 | 6 | 7 | 4 | 35.3 | 9.25 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -13.04 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.37 | 4.14 | 0.23 | -0.053 | 22 | quality (higher is better) |
| technician | 4.94 | 5.08 | -0.13 | -0.016 | 22 | quality (higher is better) |
| skeptic | 5.56 | 7.23 | -1.68 | 0.152 | 22 | severity (lower is better) |
| risk_manager | 5.61 | 4.62 | 1.0 | 0.212 | 22 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 3 | 1 | 1 | 1 | 1 | 33.3 | 39.42 |
| 40-70 | 14 | 6 | 6 | 6 | 2 | 42.9 | 9.96 |
| 70-100 | 5 | 3 | 2 | 2 | 1 | 40.0 | -23.89 |


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
| run_20261010T093857Z | 2026-10-10T09:38:57+00:00 | no | — | — | — |
| run_20261009T165039Z | 2026-10-09T16:50:39+00:00 | yes | 1 | 0 | 0.0 |
| run_20261009T135653Z | 2026-10-09T13:56:54+00:00 | yes | 1 | 1 | 0.0 |
| run_20261009T095304Z | 2026-10-09T09:53:04+00:00 | yes | 1 | 0 | 0.0 |
| run_20261009T094938Z | 2026-10-09T09:49:38+00:00 | yes | 0 | 0 | 0.0 |
