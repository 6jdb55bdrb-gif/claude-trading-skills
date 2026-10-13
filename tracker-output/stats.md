# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 37 / unreviewed 0 · TAKE/SKIP 5/32 (13.5% TAKE)

**Account (every call):** $1,136.00 (+13.60% on $1,000.00) · 100.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $968.12 (-3.19%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +0.74% — equal weight across all 37 priced call(s)

**Generated:** 2026-10-13T19:34:17+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 37 |
| Reviewed calls | 37 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 32 |
| Open | 17 |
| Right | 13 |
| Wrong | 16 |
| Neutral | 8 |
| Hit rate % | 35.1 |
| **Total PnL % (equal weight, all calls)** | +0.74% |
| Average PnL % per call | 0.74 |
| Portfolio PnL % (equal weight, TAKE only) | -6.38 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 37 | 17 | 13 | 16 | 8 | 35.1 | 0.74 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| stock | 36 | 16 | 12 | 16 | 8 | 33.3 | 0.75 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| premarket_gap | 12 | 5 | 2 | 6 | 4 | 16.7 | -8.57 |
| squeeze | 24 | 11 | 10 | 10 | 4 | 41.7 | 5.42 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 2 | 2 | 1 | 40.0 | -6.38 |
| SKIP (shadow) | 32 | 14 | 11 | 14 | 7 | 34.4 | 1.85 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -8.23 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.86 | 3.69 | 0.17 | 0.007 | 37 | quality (higher is better) |
| technician | 5.12 | 5.12 | -0.01 | -0.021 | 37 | quality (higher is better) |
| skeptic | 6.0 | 6.31 | -0.31 | 0.179 | 37 | severity (lower is better) |
| risk_manager | 5.77 | 5.1 | 0.67 | 0.156 | 37 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 2 | 1 | 3 | 2 | 16.7 | 12.63 |
| 40-70 | 25 | 13 | 11 | 9 | 5 | 44.0 | 4.46 |
| 70-100 | 6 | 2 | 1 | 4 | 1 | 16.7 | -26.67 |


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
| run_20261013T193341Z | 2026-10-13T19:33:41+00:00 | yes | — | — | — |
| run_20261013T142208Z | 2026-10-13T14:22:08+00:00 | yes | 0 | 0 | 0.0 |
| run_20261013T142126Z | 2026-10-13T14:21:26+00:00 | yes | 1 | 1 | 0.0 |
| run_20261013T135043Z | 2026-10-13T13:50:43+00:00 | yes | 0 | 4 | 0.0 |
| run_20261013T095521Z | 2026-10-13T09:55:21+00:00 | yes | 1 | 0 | 0.0 |

