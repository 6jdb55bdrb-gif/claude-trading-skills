# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 37 / unreviewed 0 · TAKE/SKIP 5/32 (13.5% TAKE)

**Account (every call):** $1,149.04 (+14.90% on $1,000.00) · 100.0% allocated · cash $-0.00

**TAKE only (the Judge's scorecard):** $968.52 (-3.15%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +0.93% — equal weight across all 37 priced call(s)

**Generated:** 2026-10-13T14:22:40+00:00<br>
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
| Right | 14 |
| Wrong | 16 |
| Neutral | 7 |
| Hit rate % | 37.8 |
| **Total PnL % (equal weight, all calls)** | +0.93% |
| Average PnL % per call | 0.93 |
| Portfolio PnL % (equal weight, TAKE only) | -6.3 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 37 | 17 | 14 | 16 | 7 | 37.8 | 0.93 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.19 |
| stock | 36 | 16 | 13 | 16 | 7 | 36.1 | 0.95 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.19 |
| premarket_gap | 12 | 5 | 2 | 6 | 4 | 16.7 | -8.44 |
| squeeze | 24 | 11 | 11 | 10 | 3 | 45.8 | 5.65 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 3 | 2 | 0 | 60.0 | -6.3 |
| SKIP (shadow) | 32 | 14 | 11 | 14 | 7 | 34.4 | 2.06 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -8.36 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.87 | 3.67 | 0.2 | 0.025 | 37 | quality (higher is better) |
| technician | 5.18 | 5.09 | 0.09 | -0.01 | 37 | quality (higher is better) |
| skeptic | 5.71 | 6.5 | -0.79 | 0.168 | 37 | severity (lower is better) |
| risk_manager | 5.86 | 5.02 | 0.84 | 0.145 | 37 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 2 | 1 | 3 | 2 | 16.7 | 12.56 |
| 40-70 | 25 | 13 | 11 | 9 | 5 | 44.0 | 4.59 |
| 70-100 | 6 | 2 | 2 | 4 | 0 | 33.3 | -25.93 |


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
| run_20261013T142208Z | 2026-10-13T14:22:08+00:00 | yes | — | — | — |
| run_20261013T142126Z | 2026-10-13T14:21:26+00:00 | yes | 1 | 1 | 0.0 |
| run_20261013T135043Z | 2026-10-13T13:50:43+00:00 | yes | 0 | 4 | 0.0 |
| run_20261013T095521Z | 2026-10-13T09:55:21+00:00 | yes | 1 | 0 | 0.0 |
| run_20261013T075826Z | 2026-10-13T07:58:26+00:00 | no | 0 | 0 | 0.0 |

