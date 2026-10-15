# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 39 / unreviewed 0 · TAKE/SKIP 7/32 (17.9% TAKE)

**Account (every call):** $1,075.69 (+7.57% on $1,000.00) · 94.0% allocated · cash $61.42

**TAKE only (the Judge's scorecard):** $917.18 (-8.28%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -1.65% — equal weight across all 39 priced call(s)

**Generated:** 2026-10-15T06:47:14+00:00<br>
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
| Right | 10 |
| Wrong | 19 |
| Neutral | 10 |
| Hit rate % | 25.6 |
| **Total PnL % (equal weight, all calls)** | -1.65% |
| Average PnL % per call | -1.65 |
| Portfolio PnL % (equal weight, TAKE only) | -11.61 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 39 | 16 | 10 | 19 | 10 | 25.6 | -1.65 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.03 |
| stock | 38 | 15 | 10 | 19 | 9 | 26.3 | -1.69 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -0.03 |
| premarket_gap | 14 | 5 | 3 | 8 | 3 | 21.4 | -10.78 |
| squeeze | 24 | 10 | 7 | 11 | 6 | 29.2 | 3.61 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 7 | 4 | 1 | 3 | 3 | 14.3 | -11.61 |
| SKIP (shadow) | 32 | 12 | 9 | 16 | 7 | 28.1 | 0.53 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -12.14 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.97 | 3.68 | 0.29 | 0.009 | 39 | quality (higher is better) |
| technician | 5.25 | 5.07 | 0.18 | -0.038 | 39 | quality (higher is better) |
| skeptic | 6.2 | 5.91 | 0.29 | 0.219 | 39 | severity (lower is better) |
| risk_manager | 5.65 | 5.24 | 0.41 | 0.123 | 39 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 11.77 |
| 40-70 | 26 | 13 | 9 | 10 | 7 | 34.6 | 2.79 |
| 70-100 | 7 | 2 | 0 | 5 | 2 | 0.0 | -29.65 |


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
| run_20261015T064704Z | 2026-10-15T06:47:04+00:00 | no | — | — | — |
| run_20261015T064251Z | 2026-10-15T06:42:51+00:00 | no | 0 | 0 | 0.0 |
| run_20261014T103051Z | 2026-10-14T10:30:51+00:00 | yes | 2 | 0 | 0.0 |
| run_20261013T193341Z | 2026-10-13T19:33:41+00:00 | yes | 0 | 0 | 0.0 |
| run_20261013T142208Z | 2026-10-13T14:22:08+00:00 | yes | 0 | 0 | 0.0 |

