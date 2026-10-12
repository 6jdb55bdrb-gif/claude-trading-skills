# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 31 / unreviewed 0 · TAKE/SKIP 5/26 (16.1% TAKE)

**Account (every call):** $1,147.45 (+14.75% on $1,000.00) · 110.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $979.99 (-2.00%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +3.93% — equal weight across all 31 priced call(s)

**Generated:** 2026-10-12T12:11:52+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 31 |
| Reviewed calls | 31 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 26 |
| Open | 19 |
| Right | 11 |
| Wrong | 9 |
| Neutral | 11 |
| Hit rate % | 35.5 |
| **Total PnL % (equal weight, all calls)** | +3.93% |
| Average PnL % per call | 3.93 |
| Portfolio PnL % (equal weight, TAKE only) | -4.0 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 31 | 19 | 11 | 9 | 11 | 35.5 | 3.93 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.26 |
| stock | 30 | 18 | 10 | 9 | 11 | 33.3 | 4.05 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.26 |
| premarket_gap | 10 | 10 | 2 | 0 | 8 | 20.0 | -2.54 |
| squeeze | 20 | 8 | 8 | 9 | 3 | 40.0 | 7.35 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -4.0 |
| SKIP (shadow) | 26 | 16 | 8 | 7 | 11 | 30.8 | 5.46 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -9.46 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.21 | 3.76 | 0.45 | -0.026 | 31 | quality (higher is better) |
| technician | 4.95 | 5.05 | -0.1 | -0.034 | 31 | quality (higher is better) |
| skeptic | 5.5 | 6.6 | -1.1 | 0.171 | 31 | severity (lower is better) |
| risk_manager | 5.55 | 4.85 | 0.7 | 0.19 | 31 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 5 | 3 | 1 | 1 | 3 | 20.0 | 23.44 |
| 40-70 | 20 | 12 | 8 | 6 | 6 | 40.0 | 5.64 |
| 70-100 | 6 | 4 | 2 | 2 | 2 | 33.3 | -18.02 |


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
| run_20261012T121118Z | 2026-10-12T12:11:18+00:00 | yes | — | — | — |
| run_20261012T103343Z | 2026-10-12T10:33:43+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T081419Z | 2026-10-12T08:14:19+00:00 | yes | 6 | 0 | 0.0 |
| run_20261010T093857Z | 2026-10-10T09:38:57+00:00 | no | 0 | 0 | 0.0 |
| run_20261009T165039Z | 2026-10-09T16:50:39+00:00 | yes | 1 | 0 | 0.0 |
