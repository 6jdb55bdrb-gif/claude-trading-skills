# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 22 / unreviewed 0 · TAKE/SKIP 5/17 (22.7% TAKE)

**Account (every call):** $1,180.54 (+18.05% on $1,000.00) · 100.0% allocated · cash $100.47

**TAKE only (the Judge's scorecard):** $986.75 (-1.32%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +8.21% — equal weight across all 22 priced call(s)

**Generated:** 2026-10-09T16:51:10+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 22 |
| Reviewed calls | 22 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 17 |
| Open | 10 |
| Right | 10 |
| Wrong | 9 |
| Neutral | 3 |
| Hit rate % | 45.5 |
| **Total PnL % (equal weight, all calls)** | +8.21% |
| Average PnL % per call | 8.21 |
| Portfolio PnL % (equal weight, TAKE only) | -2.65 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 22 | 10 | 10 | 9 | 3 | 45.5 | 8.21 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| stock | 21 | 9 | 9 | 9 | 3 | 42.9 | 8.59 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| premarket_gap | 1 | 1 | 0 | 0 | 1 | 0.0 | -4.44 |
| squeeze | 20 | 8 | 9 | 9 | 2 | 45.0 | 9.24 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -2.65 |
| SKIP (shadow) | 17 | 7 | 7 | 7 | 3 | 41.2 | 11.4 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -14.05 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.23 | 4.23 | -0.0 | -0.015 | 22 | quality (higher is better) |
| technician | 5.05 | 5.0 | 0.05 | 0.035 | 22 | quality (higher is better) |
| skeptic | 5.55 | 7.38 | -1.83 | 0.124 | 22 | severity (lower is better) |
| risk_manager | 5.85 | 4.33 | 1.52 | 0.203 | 22 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 3 | 1 | 1 | 1 | 1 | 33.3 | 39.42 |
| 40-70 | 14 | 6 | 7 | 6 | 1 | 50.0 | 13.02 |
| 70-100 | 5 | 3 | 2 | 2 | 1 | 40.0 | -24.0 |


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
| run_20261009T165039Z | 2026-10-09T16:50:39+00:00 | yes | — | — | — |
| run_20261009T135653Z | 2026-10-09T13:56:54+00:00 | yes | 1 | 1 | 0.0 |
| run_20261009T095304Z | 2026-10-09T09:53:04+00:00 | yes | 1 | 0 | 0.0 |
| run_20261009T094938Z | 2026-10-09T09:49:38+00:00 | yes | 0 | 0 | 0.0 |
| run_20261009T073355Z | 2026-10-09T07:33:56+00:00 | no | 0 | 0 | 0.0 |
