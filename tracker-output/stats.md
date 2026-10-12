# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 29 / unreviewed 0 · TAKE/SKIP 5/24 (17.2% TAKE)

**Account (every call):** $1,168.06 (+16.81% on $1,000.00) · 110.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $981.42 (-1.86%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +5.41% — equal weight across all 29 priced call(s)

**Generated:** 2026-10-12T10:34:13+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 29 |
| Reviewed calls | 29 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 24 |
| Open | 17 |
| Right | 12 |
| Wrong | 9 |
| Neutral | 8 |
| Hit rate % | 41.4 |
| **Total PnL % (equal weight, all calls)** | +5.41% |
| Average PnL % per call | 5.41 |
| Portfolio PnL % (equal weight, TAKE only) | -3.72 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 29 | 17 | 12 | 9 | 8 | 41.4 | 5.41 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.27 |
| stock | 28 | 16 | 11 | 9 | 8 | 39.3 | 5.59 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.27 |
| premarket_gap | 8 | 8 | 3 | 0 | 5 | 37.5 | -1.87 |
| squeeze | 20 | 8 | 8 | 9 | 3 | 40.0 | 8.58 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -3.72 |
| SKIP (shadow) | 24 | 14 | 9 | 7 | 8 | 37.5 | 7.31 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -11.03 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.09 | 3.86 | 0.23 | -0.028 | 29 | quality (higher is better) |
| technician | 4.96 | 5.06 | -0.1 | -0.04 | 29 | quality (higher is better) |
| skeptic | 5.5 | 6.74 | -1.24 | 0.193 | 29 | severity (lower is better) |
| risk_manager | 5.5 | 4.79 | 0.71 | 0.173 | 29 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 4 | 2 | 1 | 1 | 2 | 25.0 | 29.38 |
| 40-70 | 20 | 12 | 9 | 6 | 5 | 45.0 | 6.45 |
| 70-100 | 5 | 3 | 2 | 2 | 1 | 40.0 | -17.95 |


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
| run_20261012T103343Z | 2026-10-12T10:33:43+00:00 | yes | — | — | — |
| run_20261012T081419Z | 2026-10-12T08:14:19+00:00 | yes | 6 | 0 | 0.0 |
| run_20261010T093857Z | 2026-10-10T09:38:57+00:00 | no | 0 | 0 | 0.0 |
| run_20261009T165039Z | 2026-10-09T16:50:39+00:00 | yes | 1 | 0 | 0.0 |
| run_20261009T135653Z | 2026-10-09T13:56:54+00:00 | yes | 1 | 1 | 0.0 |
