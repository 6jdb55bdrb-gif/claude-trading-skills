# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 35 / unreviewed 0 · TAKE/SKIP 5/30 (14.3% TAKE)

**Account (every call):** $1,136.04 (+13.60% on $1,000.00) · 100.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $975.44 (-2.46%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +1.81% — equal weight across all 35 priced call(s)

**Generated:** 2026-10-12T20:36:14+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 35 |
| Reviewed calls | 35 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 30 |
| Open | 20 |
| Right | 12 |
| Wrong | 12 |
| Neutral | 11 |
| Hit rate % | 34.3 |
| **Total PnL % (equal weight, all calls)** | +1.81% |
| Average PnL % per call | 1.81 |
| Portfolio PnL % (equal weight, TAKE only) | -4.91 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 35 | 20 | 12 | 12 | 11 | 34.3 | 1.81 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.17 |
| stock | 34 | 19 | 11 | 12 | 11 | 32.4 | 1.86 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.17 |
| premarket_gap | 11 | 8 | 3 | 3 | 5 | 27.3 | -4.63 |
| squeeze | 23 | 11 | 8 | 9 | 6 | 34.8 | 4.96 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -4.91 |
| SKIP (shadow) | 30 | 17 | 9 | 10 | 11 | 30.0 | 2.93 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -7.85 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.09 | 3.64 | 0.45 | -0.021 | 35 | quality (higher is better) |
| technician | 4.96 | 5.17 | -0.22 | -0.046 | 35 | quality (higher is better) |
| skeptic | 5.88 | 6.37 | -0.49 | 0.174 | 35 | severity (lower is better) |
| risk_manager | 5.5 | 5.28 | 0.22 | 0.153 | 35 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 3 | 2 | 2 | 2 | 33.3 | 15.06 |
| 40-70 | 23 | 14 | 8 | 7 | 8 | 34.8 | 5.32 |
| 70-100 | 6 | 3 | 2 | 3 | 1 | 33.3 | -24.89 |


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
| run_20261012T203539Z | 2026-10-12T20:35:39+00:00 | yes | — | — | — |
| run_20261012T154213Z | 2026-10-12T15:42:13+00:00 | yes | 0 | 1 | 0.0 |
| run_20261012T153047Z | 2026-10-12T15:30:47+00:00 | yes | 0 | 1 | 0.0 |
| run_20261012T150156Z | 2026-10-12T15:01:56+00:00 | yes | 0 | 0 | 0.0 |
| run_20261012T140336Z | 2026-10-12T14:03:36+00:00 | yes | 2 | 1 | 0.0 |
