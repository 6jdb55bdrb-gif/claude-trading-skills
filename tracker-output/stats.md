# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 20 / unreviewed 0 · TAKE/SKIP 5/15 (25.0% TAKE)

**Account (every call):** $1,157.11 (+15.71% on $1,000.00) · 90.0% allocated · cash $226.31

**TAKE only (the Judge's scorecard):** $969.14 (-3.09%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +7.86% — equal weight across all 20 priced call(s)

**Generated:** 2026-10-09T09:53:29+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 20 |
| Reviewed calls | 20 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 15 |
| Open | 9 |
| Right | 7 |
| Wrong | 8 |
| Neutral | 5 |
| Hit rate % | 35.0 |
| **Total PnL % (equal weight, all calls)** | +7.86% |
| Average PnL % per call | 7.86 |
| Portfolio PnL % (equal weight, TAKE only) | -6.17 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 20 | 9 | 7 | 8 | 5 | 35.0 | 7.86 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.54 |
| stock | 19 | 8 | 7 | 8 | 4 | 36.8 | 8.3 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.54 |
| premarket_gap | 1 | 1 | 0 | 0 | 1 | 0.0 | 0.0 |
| squeeze | 18 | 7 | 7 | 8 | 3 | 38.9 | 8.76 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 2 | 2 | 1 | 40.0 | -6.17 |
| SKIP (shadow) | 15 | 6 | 5 | 6 | 4 | 33.3 | 12.53 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -18.7 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.61 | 4.14 | 0.48 | -0.06 | 20 | quality (higher is better) |
| technician | 5.36 | 4.69 | 0.66 | -0.005 | 20 | quality (higher is better) |
| skeptic | 5.86 | 7.15 | -1.3 | 0.171 | 20 | severity (lower is better) |
| risk_manager | 5.64 | 4.42 | 1.22 | 0.227 | 20 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 3 | 1 | 1 | 1 | 1 | 33.3 | 40.9 |
| 40-70 | 12 | 5 | 6 | 5 | 1 | 50.0 | 12.98 |
| 70-100 | 5 | 3 | 0 | 2 | 3 | 0.0 | -24.28 |


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
| run_20261009T095304Z | 2026-10-09T09:53:04+00:00 | yes | — | — | — |
| run_20261009T094938Z | 2026-10-09T09:49:38+00:00 | yes | 0 | 0 | 0.0 |
| run_20261009T073355Z | 2026-10-09T07:33:56+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T175505Z | 2026-10-08T17:55:05+00:00 | yes | 0 | 0 | 0.0 |
| run_20261008T171310Z | 2026-10-08T17:13:10+00:00 | yes | 3 | 1 | 0.0 |
