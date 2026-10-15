# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 39 / unreviewed 0 · TAKE/SKIP 7/32 (17.9% TAKE)

**Account (every call):** $1,079.96 (+8.00% on $1,000.00) · 94.0% allocated · cash $61.42

**TAKE only (the Judge's scorecard):** $923.11 (-7.69%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -1.76% — equal weight across all 39 priced call(s)

**Generated:** 2026-10-15T11:38:51+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 39 |
| Reviewed calls | 39 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 7 |
| Shadow (SKIP) calls | 32 |
| Open | 16 |
| Right | 9 |
| Wrong | 19 |
| Neutral | 11 |
| Hit rate % | 23.1 |
| **Total PnL % (equal weight, all calls)** | -1.76% |
| Average PnL % per call | -1.76 |
| Portfolio PnL % (equal weight, TAKE only) | -10.61 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 39 | 16 | 9 | 19 | 11 | 23.1 | -1.76 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.05 |
| stock | 38 | 15 | 9 | 19 | 10 | 23.7 | -1.81 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.05 |
| premarket_gap | 14 | 5 | 3 | 8 | 3 | 21.4 | -10.68 |
| squeeze | 24 | 10 | 6 | 11 | 7 | 25.0 | 3.37 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 7 | 4 | 1 | 3 | 3 | 14.3 | -10.61 |
| SKIP (shadow) | 32 | 12 | 8 | 16 | 8 | 25.0 | 0.17 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -10.79 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.14 | 3.63 | 0.51 | 0.011 | 39 | quality (higher is better) |
| technician | 5.17 | 5.1 | 0.07 | -0.042 | 39 | quality (higher is better) |
| skeptic | 6.28 | 5.9 | 0.38 | 0.212 | 39 | severity (lower is better) |
| risk_manager | 5.39 | 5.33 | 0.06 | 0.121 | 39 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 11.77 |
| 40-70 | 26 | 13 | 8 | 10 | 8 | 30.8 | 2.61 |
| 70-100 | 7 | 2 | 0 | 5 | 2 | 0.0 | -29.59 |


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
| run_20261015T113816Z | 2026-10-15T11:38:16+00:00 | yes | — | — | — |
| run_20261015T064704Z | 2026-10-15T06:47:04+00:00 | no | 0 | 1 | 0.0 |
| run_20261015T064251Z | 2026-10-15T06:42:51+00:00 | no | 0 | 0 | 0.0 |
| run_20261014T103051Z | 2026-10-14T10:30:51+00:00 | yes | 2 | 0 | 0.0 |
| run_20261013T193341Z | 2026-10-13T19:33:41+00:00 | yes | 0 | 0 | 0.0 |

