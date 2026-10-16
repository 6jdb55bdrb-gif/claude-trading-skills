# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 41 / unreviewed 0 · TAKE/SKIP 9/32 (22.0% TAKE)

**Account (every call):** $1,086.88 (+8.69% on $1,000.00) · 91.6% allocated · cash $87.96

**TAKE only (the Judge's scorecard):** $927.13 (-7.29%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -0.92% — equal weight across all 41 priced call(s)

**Generated:** 2026-10-16T14:06:18+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 41 |
| Reviewed calls | 41 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 9 |
| Shadow (SKIP) calls | 32 |
| Open | 16 |
| Right | 12 |
| Wrong | 20 |
| Neutral | 9 |
| Hit rate % | 29.3 |
| **Total PnL % (equal weight, all calls)** | -0.92% |
| Average PnL % per call | -0.92 |
| Portfolio PnL % (equal weight, TAKE only) | -7.75 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 41 | 16 | 12 | 20 | 9 | 29.3 | -0.92 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.05 |
| stock | 40 | 15 | 12 | 20 | 8 | 30.0 | -0.94 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.05 |
| momentum_breakout | 1 | 1 | 0 | 0 | 1 | 0.0 | 0.0 |
| premarket_gap | 15 | 6 | 3 | 8 | 4 | 20.0 | -9.78 |
| squeeze | 24 | 8 | 9 | 12 | 3 | 37.5 | 4.55 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 9 | 6 | 2 | 3 | 4 | 22.2 | -7.75 |
| SKIP (shadow) | 32 | 10 | 10 | 17 | 5 | 31.2 | 1.01 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -8.75 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.92 | 3.72 | 0.2 | -0.022 | 41 | quality (higher is better) |
| technician | 5.38 | 5.03 | 0.34 | -0.044 | 41 | quality (higher is better) |
| skeptic | 5.92 | 5.74 | 0.18 | 0.195 | 41 | severity (lower is better) |
| risk_manager | 5.79 | 5.26 | 0.53 | 0.15 | 41 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 12.13 |
| 40-70 | 27 | 12 | 11 | 11 | 5 | 40.7 | 3.96 |
| 70-100 | 8 | 3 | 0 | 5 | 3 | 0.0 | -27.16 |


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
| run_20261016T140541Z | 2026-10-16T14:05:41+00:00 | yes | — | — | — |
| run_20261016T125656Z | 2026-10-16T12:56:57+00:00 | yes | 1 | 0 | 0.0 |
| run_20261015T113816Z | 2026-10-15T11:38:16+00:00 | yes | 0 | 0 | 0.0 |
| run_20261015T064704Z | 2026-10-15T06:47:04+00:00 | no | 0 | 1 | 0.0 |
| run_20261015T064251Z | 2026-10-15T06:42:51+00:00 | no | 0 | 0 | 0.0 |

