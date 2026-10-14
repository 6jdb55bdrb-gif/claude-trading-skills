# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 39 / unreviewed 0 · TAKE/SKIP 7/32 (17.9% TAKE)

**Account (every call):** $1,141.62 (+14.16% on $1,000.00) · 100.0% allocated · cash $0.00

**TAKE only (the Judge's scorecard):** $971.27 (-2.87%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +0.62% — equal weight across all 39 priced call(s)

**Generated:** 2026-10-14T10:31:28+00:00<br>
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
| Open | 17 |
| Right | 13 |
| Wrong | 18 |
| Neutral | 8 |
| Hit rate % | 33.3 |
| **Total PnL % (equal weight, all calls)** | +0.62% |
| Average PnL % per call | 0.62 |
| Portfolio PnL % (equal weight, TAKE only) | -4.1 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 39 | 17 | 13 | 18 | 8 | 33.3 | 0.62 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.21 |
| stock | 38 | 16 | 12 | 18 | 8 | 31.6 | 0.63 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.21 |
| premarket_gap | 14 | 6 | 2 | 7 | 5 | 14.3 | -7.75 |
| squeeze | 24 | 10 | 10 | 11 | 3 | 41.7 | 5.52 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 7 | 5 | 2 | 2 | 3 | 28.6 | -4.1 |
| SKIP (shadow) | 32 | 12 | 11 | 16 | 5 | 34.4 | 1.66 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -5.76 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.86 | 3.7 | 0.17 | 0.015 | 39 | quality (higher is better) |
| technician | 5.12 | 5.12 | 0.0 | -0.017 | 39 | quality (higher is better) |
| skeptic | 6.0 | 5.98 | 0.02 | 0.167 | 39 | severity (lower is better) |
| risk_manager | 5.77 | 5.13 | 0.63 | 0.151 | 39 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 12.75 |
| 40-70 | 26 | 13 | 11 | 10 | 5 | 42.3 | 4.13 |
| 70-100 | 7 | 3 | 1 | 4 | 2 | 14.3 | -22.82 |


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
| run_20261014T103051Z | 2026-10-14T10:30:51+00:00 | yes | — | — | — |
| run_20261013T193341Z | 2026-10-13T19:33:41+00:00 | yes | 0 | 0 | 0.0 |
| run_20261013T142208Z | 2026-10-13T14:22:08+00:00 | yes | 0 | 0 | 0.0 |
| run_20261013T142126Z | 2026-10-13T14:21:26+00:00 | yes | 1 | 1 | 0.0 |
| run_20261013T135043Z | 2026-10-13T13:50:43+00:00 | yes | 0 | 4 | 0.0 |

