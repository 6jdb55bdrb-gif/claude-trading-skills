# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 36 / unreviewed 0 · TAKE/SKIP 5/31 (13.9% TAKE)

**Account (every call):** $1,130.38 (+13.04% on $1,000.00) · 100.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $985.06 (-1.49%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +0.66% — equal weight across all 36 priced call(s)

**Generated:** 2026-10-13T09:55:57+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 36 |
| Reviewed calls | 36 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 31 |
| Open | 21 |
| Right | 12 |
| Wrong | 12 |
| Neutral | 12 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +0.66% |
| Average PnL % per call | 0.66 |
| Portfolio PnL % (equal weight, TAKE only) | -2.99 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 36 | 21 | 12 | 12 | 12 | 33.3 | 0.66 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| stock | 35 | 20 | 11 | 12 | 12 | 31.4 | 0.67 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| premarket_gap | 12 | 9 | 2 | 3 | 7 | 16.7 | -7.99 |
| squeeze | 23 | 11 | 9 | 9 | 5 | 39.1 | 5.19 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -2.99 |
| SKIP (shadow) | 31 | 18 | 9 | 10 | 12 | 29.0 | 1.24 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -4.23 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.06 | 3.63 | 0.43 | -0.01 | 36 | quality (higher is better) |
| technician | 5.04 | 5.12 | -0.08 | -0.035 | 36 | quality (higher is better) |
| skeptic | 5.5 | 6.52 | -1.02 | 0.166 | 36 | severity (lower is better) |
| risk_manager | 5.75 | 5.15 | 0.6 | 0.166 | 36 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 3 | 1 | 2 | 3 | 16.7 | 14.07 |
| 40-70 | 24 | 15 | 9 | 7 | 8 | 37.5 | 3.79 |
| 70-100 | 6 | 3 | 2 | 3 | 1 | 33.3 | -25.3 |


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
| run_20261013T095521Z | 2026-10-13T09:55:21+00:00 | yes | — | — | — |
| run_20261013T075826Z | 2026-10-13T07:58:26+00:00 | no | 0 | 0 | 0.0 |
| run_20261012T203539Z | 2026-10-12T20:35:39+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T154213Z | 2026-10-12T15:42:13+00:00 | yes | 0 | 1 | 0.0 |
| run_20261012T153047Z | 2026-10-12T15:30:47+00:00 | yes | 0 | 1 | 0.0 |
