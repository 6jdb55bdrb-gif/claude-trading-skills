# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 34 / unreviewed 0 · TAKE/SKIP 5/29 (14.7% TAKE)

**Account (every call):** $1,141.90 (+14.19% on $1,000.00) · 110.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $977.23 (-2.28%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +2.38% — equal weight across all 34 priced call(s)

**Generated:** 2026-10-12T14:04:19+00:00<br>
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
| Open | 21 |
| Right | 12 |
| Wrong | 10 |
| Neutral | 12 |
| Hit rate % | 35.3 |
| **Total PnL % (equal weight, all calls)** | +2.38% |
| Average PnL % per call | 2.38 |
| Portfolio PnL % (equal weight, TAKE only) | -4.56 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 34 | 21 | 12 | 10 | 12 | 35.3 | 2.38 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.19 |
| stock | 33 | 20 | 11 | 10 | 12 | 33.3 | 2.45 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.19 |
| premarket_gap | 11 | 10 | 3 | 1 | 7 | 27.3 | -4.54 |
| squeeze | 22 | 10 | 8 | 9 | 5 | 36.4 | 5.95 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -4.56 |
| SKIP (shadow) | 29 | 18 | 9 | 8 | 12 | 31.0 | 3.58 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -8.14 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.09 | 3.69 | 0.41 | -0.025 | 34 | quality (higher is better) |
| technician | 4.96 | 5.14 | -0.18 | -0.04 | 34 | quality (higher is better) |
| skeptic | 5.88 | 6.34 | -0.47 | 0.181 | 34 | severity (lower is better) |
| risk_manager | 5.5 | 5.16 | 0.34 | 0.162 | 34 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 4 | 2 | 1 | 3 | 33.3 | 17.82 |
| 40-70 | 22 | 14 | 8 | 6 | 8 | 36.4 | 5.62 |
| 70-100 | 6 | 3 | 2 | 3 | 1 | 33.3 | -24.9 |


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
| run_20261012T140336Z | 2026-10-12T14:03:36+00:00 | yes | — | — | — |
| run_20261012T132717Z | 2026-10-12T13:27:17+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T121118Z | 2026-10-12T12:11:18+00:00 | yes | 2 | 0 | 0.0 |
| run_20261012T103343Z | 2026-10-12T10:33:43+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T081419Z | 2026-10-12T08:14:19+00:00 | yes | 6 | 0 | 0.0 |
