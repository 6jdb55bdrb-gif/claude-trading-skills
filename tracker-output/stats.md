# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 40 / unreviewed 0 · TAKE/SKIP 8/32 (20.0% TAKE)

**Account (every call):** $1,149.16 (+14.92% on $1,000.00) · 94.8% allocated · cash $52.18

**TAKE only (the Judge's scorecard):** $967.31 (-3.27%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +1.35% — equal weight across all 40 priced call(s)

**Generated:** 2026-10-16T12:57:38+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 40 |
| Reviewed calls | 40 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 8 |
| Shadow (SKIP) calls | 32 |
| Open | 16 |
| Right | 13 |
| Wrong | 20 |
| Neutral | 7 |
| Hit rate % | 32.5 |
| **Total PnL % (equal weight, all calls)** | +1.35% |
| Average PnL % per call | 1.35 |
| Portfolio PnL % (equal weight, TAKE only) | -3.31 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 40 | 16 | 13 | 20 | 7 | 32.5 | 1.35 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.05 |
| stock | 39 | 15 | 13 | 20 | 6 | 33.3 | 1.38 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.05 |
| premarket_gap | 15 | 6 | 3 | 8 | 4 | 20.0 | -6.1 |
| squeeze | 24 | 9 | 10 | 12 | 2 | 41.7 | 6.06 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 8 | 5 | 3 | 3 | 2 | 37.5 | -3.31 |
| SKIP (shadow) | 32 | 11 | 10 | 17 | 5 | 31.2 | 2.51 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -5.83 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.91 | 3.69 | 0.22 | -0.007 | 40 | quality (higher is better) |
| technician | 5.42 | 4.96 | 0.46 | -0.016 | 40 | quality (higher is better) |
| skeptic | 5.62 | 6.02 | -0.4 | 0.157 | 40 | severity (lower is better) |
| risk_manager | 5.88 | 5.09 | 0.79 | 0.157 | 40 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 13.16 |
| 40-70 | 26 | 12 | 12 | 11 | 3 | 46.2 | 6.87 |
| 70-100 | 8 | 3 | 0 | 5 | 3 | 0.0 | -25.47 |


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
| run_20261016T125656Z | 2026-10-16T12:56:57+00:00 | yes | — | — | — |
| run_20261015T113816Z | 2026-10-15T11:38:16+00:00 | yes | 0 | 0 | 0.0 |
| run_20261015T064704Z | 2026-10-15T06:47:04+00:00 | no | 0 | 1 | 0.0 |
| run_20261015T064251Z | 2026-10-15T06:42:51+00:00 | no | 0 | 0 | 0.0 |
| run_20261014T103051Z | 2026-10-14T10:30:51+00:00 | yes | 2 | 0 | 0.0 |

