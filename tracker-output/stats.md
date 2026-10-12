# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 34 / unreviewed 0 · TAKE/SKIP 5/29 (14.7% TAKE)

**Account (every call):** $1,123.69 (+12.37% on $1,000.00) · 100.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $976.97 (-2.30%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +2.35% — equal weight across all 34 priced call(s)

**Generated:** 2026-10-12T15:42:43+00:00<br>
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
| Open | 19 |
| Right | 13 |
| Wrong | 12 |
| Neutral | 9 |
| Hit rate % | 38.2 |
| **Total PnL % (equal weight, all calls)** | +2.35% |
| Average PnL % per call | 2.35 |
| Portfolio PnL % (equal weight, TAKE only) | -4.61 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 34 | 19 | 13 | 12 | 9 | 38.2 | 2.35 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.19 |
| stock | 33 | 18 | 12 | 12 | 9 | 36.4 | 2.41 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.19 |
| premarket_gap | 11 | 8 | 3 | 3 | 5 | 27.3 | -2.56 |
| squeeze | 22 | 10 | 9 | 9 | 4 | 40.9 | 4.9 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -4.61 |
| SKIP (shadow) | 29 | 16 | 10 | 10 | 9 | 34.5 | 3.55 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -8.15 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.96 | 3.75 | 0.21 | -0.036 | 34 | quality (higher is better) |
| technician | 5.04 | 5.1 | -0.06 | -0.051 | 34 | quality (higher is better) |
| skeptic | 5.5 | 6.6 | -1.1 | 0.167 | 34 | severity (lower is better) |
| risk_manager | 5.69 | 5.02 | 0.67 | 0.162 | 34 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 3 | 1 | 2 | 3 | 16.7 | 14.68 |
| 40-70 | 22 | 13 | 10 | 7 | 5 | 45.5 | 6.34 |
| 70-100 | 6 | 3 | 2 | 3 | 1 | 33.3 | -24.62 |


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
| run_20261012T154213Z | 2026-10-12T15:42:13+00:00 | yes | — | — | — |
| run_20261012T153047Z | 2026-10-12T15:30:47+00:00 | yes | 0 | 1 | 0.0 |
| run_20261012T150156Z | 2026-10-12T15:01:56+00:00 | yes | 0 | 0 | 0.0 |
| run_20261012T140336Z | 2026-10-12T14:03:36+00:00 | yes | 2 | 1 | 0.0 |
| run_20261012T132717Z | 2026-10-12T13:27:17+00:00 | yes | 1 | 0 | 0.0 |
