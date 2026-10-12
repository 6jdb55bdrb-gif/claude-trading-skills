# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 34 / unreviewed 0 · TAKE/SKIP 5/29 (14.7% TAKE)

**Account (every call):** $1,125.18 (+12.52% on $1,000.00) · 100.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $976.80 (-2.32%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +3.15% — equal weight across all 34 priced call(s)

**Generated:** 2026-10-12T15:31:19+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 34 |
| Reviewed calls | 34 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 29 |
| Open | 20 |
| Right | 13 |
| Wrong | 11 |
| Neutral | 10 |
| Hit rate % | 38.2 |
| **Total PnL % (equal weight, all calls)** | +3.15% |
| Average PnL % per call | 3.15 |
| Portfolio PnL % (equal weight, TAKE only) | -4.64 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 34 | 20 | 13 | 11 | 10 | 38.2 | 3.15 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| stock | 33 | 19 | 12 | 11 | 10 | 36.4 | 3.24 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| premarket_gap | 11 | 9 | 3 | 2 | 6 | 27.3 | -0.13 |
| squeeze | 22 | 10 | 9 | 9 | 4 | 40.9 | 4.93 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -4.64 |
| SKIP (shadow) | 29 | 17 | 10 | 9 | 10 | 34.5 | 4.5 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -9.14 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.96 | 3.75 | 0.21 | -0.045 | 34 | quality (higher is better) |
| technician | 5.04 | 5.1 | -0.06 | -0.052 | 34 | quality (higher is better) |
| skeptic | 5.5 | 6.6 | -1.1 | 0.175 | 34 | severity (lower is better) |
| risk_manager | 5.69 | 5.02 | 0.67 | 0.16 | 34 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 4 | 1 | 1 | 4 | 16.7 | 16.77 |
| 40-70 | 22 | 13 | 10 | 7 | 5 | 45.5 | 7.01 |
| 70-100 | 6 | 3 | 2 | 3 | 1 | 33.3 | -24.58 |


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
| run_20261012T153047Z | 2026-10-12T15:30:47+00:00 | yes | — | — | — |
| run_20261012T150156Z | 2026-10-12T15:01:56+00:00 | yes | 0 | 0 | 0.0 |
| run_20261012T140336Z | 2026-10-12T14:03:36+00:00 | yes | 2 | 1 | 0.0 |
| run_20261012T132717Z | 2026-10-12T13:27:17+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T121118Z | 2026-10-12T12:11:18+00:00 | yes | 2 | 0 | 0.0 |
