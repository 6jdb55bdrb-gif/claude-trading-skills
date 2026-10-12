# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 32 / unreviewed 0 · TAKE/SKIP 5/27 (15.6% TAKE)

**Account (every call):** $1,148.79 (+14.88% on $1,000.00) · 110.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $980.14 (-1.99%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +4.01% — equal weight across all 32 priced call(s)

**Generated:** 2026-10-12T13:27:50+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 32 |
| Reviewed calls | 32 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 27 |
| Open | 20 |
| Right | 11 |
| Wrong | 9 |
| Neutral | 12 |
| Hit rate % | 34.4 |
| **Total PnL % (equal weight, all calls)** | +4.01% |
| Average PnL % per call | 4.01 |
| Portfolio PnL % (equal weight, TAKE only) | -3.97 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 32 | 20 | 11 | 9 | 12 | 34.4 | 4.01 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.27 |
| stock | 31 | 19 | 10 | 9 | 12 | 32.3 | 4.13 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.27 |
| premarket_gap | 11 | 11 | 3 | 0 | 8 | 27.3 | -1.23 |
| squeeze | 20 | 8 | 7 | 9 | 4 | 35.0 | 7.08 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -3.97 |
| SKIP (shadow) | 27 | 17 | 8 | 7 | 12 | 29.6 | 5.49 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -9.46 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.16 | 3.74 | 0.43 | -0.024 | 32 | quality (higher is better) |
| technician | 4.86 | 5.1 | -0.23 | -0.031 | 32 | quality (higher is better) |
| skeptic | 5.27 | 6.88 | -1.61 | 0.146 | 32 | severity (lower is better) |
| risk_manager | 5.59 | 4.83 | 0.76 | 0.195 | 32 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 4 | 1 | 1 | 4 | 16.7 | 19.2 |
| 40-70 | 20 | 12 | 7 | 6 | 7 | 35.0 | 6.03 |
| 70-100 | 6 | 4 | 3 | 2 | 1 | 50.0 | -17.92 |


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
| run_20261012T132717Z | 2026-10-12T13:27:17+00:00 | yes | — | — | — |
| run_20261012T121118Z | 2026-10-12T12:11:18+00:00 | yes | 2 | 0 | 0.0 |
| run_20261012T103343Z | 2026-10-12T10:33:43+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T081419Z | 2026-10-12T08:14:19+00:00 | yes | 6 | 0 | 0.0 |
| run_20261010T093857Z | 2026-10-10T09:38:57+00:00 | no | 0 | 0 | 0.0 |
