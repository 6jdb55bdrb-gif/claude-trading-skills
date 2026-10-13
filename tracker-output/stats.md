# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 36 / unreviewed 0 · TAKE/SKIP 5/31 (13.9% TAKE)

**Account (every call):** $1,144.59 (+14.46% on $1,000.00) · 100.0% allocated · cash $0.55

**TAKE only (the Judge's scorecard):** $974.12 (-2.59%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +0.75% — equal weight across all 36 priced call(s)

**Generated:** 2026-10-13T13:51:18+00:00<br>
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
| Open | 17 |
| Right | 11 |
| Wrong | 15 |
| Neutral | 10 |
| Hit rate % | 30.6 |
| **Total PnL % (equal weight, all calls)** | +0.75% |
| Average PnL % per call | 0.75 |
| Portfolio PnL % (equal weight, TAKE only) | -5.18 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 36 | 17 | 11 | 15 | 10 | 30.6 | 0.75 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.21 |
| stock | 35 | 16 | 10 | 15 | 10 | 28.6 | 0.77 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.21 |
| premarket_gap | 12 | 5 | 2 | 6 | 4 | 16.7 | -8.55 |
| squeeze | 23 | 11 | 8 | 9 | 6 | 34.8 | 5.63 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -5.18 |
| SKIP (shadow) | 31 | 14 | 8 | 13 | 10 | 25.8 | 1.71 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -6.88 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.02 | 3.67 | 0.35 | 0.018 | 36 | quality (higher is better) |
| technician | 4.95 | 5.16 | -0.21 | -0.018 | 36 | quality (higher is better) |
| skeptic | 5.59 | 6.44 | -0.85 | 0.172 | 36 | severity (lower is better) |
| risk_manager | 5.82 | 5.14 | 0.68 | 0.147 | 36 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 2 | 1 | 3 | 2 | 16.7 | 12.99 |
| 40-70 | 24 | 12 | 8 | 9 | 7 | 33.3 | 4.21 |
| 70-100 | 6 | 3 | 2 | 3 | 1 | 33.3 | -25.33 |


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
| run_20261013T135043Z | 2026-10-13T13:50:43+00:00 | yes | — | — | — |
| run_20261013T095521Z | 2026-10-13T09:55:21+00:00 | yes | 1 | 0 | 0.0 |
| run_20261013T075826Z | 2026-10-13T07:58:26+00:00 | no | 0 | 0 | 0.0 |
| run_20261012T203539Z | 2026-10-12T20:35:39+00:00 | yes | 1 | 0 | 0.0 |
| run_20261012T154213Z | 2026-10-12T15:42:13+00:00 | yes | 0 | 1 | 0.0 |
