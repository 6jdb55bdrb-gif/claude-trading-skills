# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 28 / unreviewed 0 · TAKE/SKIP 5/23 (17.9% TAKE)

**Account (every call):** $1,147.76 (+14.78% on $1,000.00) · 110.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $981.23 (-1.88%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +5.28% — equal weight across all 28 priced call(s)

**Generated:** 2026-10-12T08:15:02+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 28 |
| Reviewed calls | 28 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 23 |
| Open | 16 |
| Right | 10 |
| Wrong | 9 |
| Neutral | 9 |
| Hit rate % | 35.7 |
| **Total PnL % (equal weight, all calls)** | +5.28% |
| Average PnL % per call | 5.28 |
| Portfolio PnL % (equal weight, TAKE only) | -3.75 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 28 | 16 | 10 | 9 | 9 | 35.7 | 5.28 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.21 |
| stock | 27 | 15 | 9 | 9 | 9 | 33.3 | 5.46 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.21 |
| premarket_gap | 7 | 7 | 0 | 0 | 7 | 0.0 | -0.63 |
| squeeze | 20 | 8 | 9 | 9 | 2 | 45.0 | 7.6 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -3.75 |
| SKIP (shadow) | 23 | 13 | 7 | 7 | 9 | 30.4 | 7.24 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -11.0 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.33 | 3.81 | 0.52 | -0.03 | 28 | quality (higher is better) |
| technician | 5.05 | 5.0 | 0.05 | -0.01 | 28 | quality (higher is better) |
| skeptic | 5.45 | 6.58 | -1.13 | 0.155 | 28 | severity (lower is better) |
| risk_manager | 5.6 | 4.81 | 0.79 | 0.203 | 28 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 3 | 1 | 1 | 1 | 1 | 33.3 | 39.42 |
| 40-70 | 20 | 12 | 7 | 6 | 7 | 35.0 | 7.32 |
| 70-100 | 5 | 3 | 2 | 2 | 1 | 40.0 | -23.39 |


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
| run_20261012T081419Z | 2026-10-12T08:14:19+00:00 | yes | — | — | — |
| run_20261010T093857Z | 2026-10-10T09:38:57+00:00 | no | 0 | 0 | 0.0 |
| run_20261009T165039Z | 2026-10-09T16:50:39+00:00 | yes | 1 | 0 | 0.0 |
| run_20261009T135653Z | 2026-10-09T13:56:54+00:00 | yes | 1 | 1 | 0.0 |
| run_20261009T095304Z | 2026-10-09T09:53:04+00:00 | yes | 1 | 0 | 0.0 |
