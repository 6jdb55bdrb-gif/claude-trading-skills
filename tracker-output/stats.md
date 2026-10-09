# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 21 / unreviewed 0 · TAKE/SKIP 5/16 (23.8% TAKE)

**Account (every call):** $1,164.81 (+16.48% on $1,000.00) · 90.0% allocated · cash $200.47

**TAKE only (the Judge's scorecard):** $982.53 (-1.75%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +7.85% — equal weight across all 21 priced call(s)

**Generated:** 2026-10-09T13:57:24+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 21 |
| Reviewed calls | 21 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 16 |
| Open | 9 |
| Right | 8 |
| Wrong | 9 |
| Neutral | 4 |
| Hit rate % | 38.1 |
| **Total PnL % (equal weight, all calls)** | +7.85% |
| Average PnL % per call | 7.85 |
| Portfolio PnL % (equal weight, TAKE only) | -3.49 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 21 | 9 | 8 | 9 | 4 | 38.1 | 7.85 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| stock | 20 | 8 | 7 | 9 | 4 | 35.0 | 8.23 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| premarket_gap | 1 | 1 | 0 | 0 | 1 | 0.0 | -4.07 |
| squeeze | 19 | 7 | 7 | 9 | 3 | 36.8 | 8.88 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -3.49 |
| SKIP (shadow) | 16 | 6 | 5 | 7 | 4 | 31.2 | 11.39 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -14.89 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.35 | 4.18 | 0.17 | -0.03 | 21 | quality (higher is better) |
| technician | 4.81 | 5.08 | -0.26 | 0.015 | 21 | quality (higher is better) |
| skeptic | 5.69 | 7.23 | -1.54 | 0.139 | 21 | severity (lower is better) |
| risk_manager | 5.69 | 4.58 | 1.11 | 0.204 | 21 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 3 | 1 | 1 | 1 | 1 | 33.3 | 39.54 |
| 40-70 | 13 | 5 | 5 | 6 | 2 | 38.5 | 12.6 |
| 70-100 | 5 | 3 | 2 | 2 | 1 | 40.0 | -23.52 |


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
| run_20261009T135653Z | 2026-10-09T13:56:54+00:00 | yes | — | — | — |
| run_20261009T095304Z | 2026-10-09T09:53:04+00:00 | yes | 1 | 0 | 0.0 |
| run_20261009T094938Z | 2026-10-09T09:49:38+00:00 | yes | 0 | 0 | 0.0 |
| run_20261009T073355Z | 2026-10-09T07:33:56+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T175505Z | 2026-10-08T17:55:05+00:00 | yes | 0 | 0 | 0.0 |
