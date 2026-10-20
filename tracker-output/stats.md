# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 43 / unreviewed 0 · TAKE/SKIP 9/34 (20.9% TAKE)

**Account (every call):** $1,060.73 (+6.07% on $1,000.00) · 93.6% allocated · cash $66.35

**TAKE only (the Judge's scorecard):** $901.06 (-9.89%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -2.15% — equal weight across all 43 priced call(s)

**Generated:** 2026-10-20T13:31:14+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 43 |
| Reviewed calls | 43 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 9 |
| Shadow (SKIP) calls | 34 |
| Open | 15 |
| Right | 12 |
| Wrong | 22 |
| Neutral | 9 |
| Hit rate % | 27.9 |
| **Total PnL % (equal weight, all calls)** | -2.15% |
| Average PnL % per call | -2.15 |
| Portfolio PnL % (equal weight, TAKE only) | -10.84 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 43 | 15 | 12 | 22 | 9 | 27.9 | -2.15 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -2.2 |
| stock | 42 | 14 | 12 | 22 | 8 | 28.6 | -2.15 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -2.2 |
| momentum_breakout | 1 | 1 | 0 | 0 | 1 | 0.0 | -2.4 |
| premarket_gap | 16 | 5 | 3 | 9 | 4 | 18.8 | -10.53 |
| squeeze | 25 | 8 | 9 | 13 | 3 | 36.0 | 3.22 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 9 | 4 | 2 | 4 | 3 | 22.2 | -10.84 |
| SKIP (shadow) | 34 | 11 | 10 | 18 | 6 | 29.4 | 0.14 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -10.98 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.97 | 3.66 | 0.31 | -0.006 | 43 | quality (higher is better) |
| technician | 5.38 | 5.06 | 0.31 | -0.05 | 43 | quality (higher is better) |
| skeptic | 5.96 | 5.82 | 0.14 | 0.212 | 43 | severity (lower is better) |
| risk_manager | 5.96 | 5.26 | 0.7 | 0.127 | 43 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 11.28 |
| 40-70 | 29 | 11 | 11 | 13 | 5 | 37.9 | 1.79 |
| 70-100 | 8 | 3 | 0 | 5 | 3 | 0.0 | -26.53 |


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
| run_20261020T133047Z | 2026-10-20T13:30:47+00:00 | yes | — | — | — |
| run_20261020T092000Z | 2026-10-20T09:20:00+00:00 | yes | 1 | 0 | 0.0 |
| run_20261019T182115Z | 2026-10-19T18:21:15+00:00 | yes | 0 | 1 | 0.0 |
| run_20261019T145622Z | 2026-10-19T14:56:22+00:00 | yes | 1 | 1 | 0.0 |
| run_20261019T144714Z | 2026-10-19T14:47:14+00:00 | yes | 0 | 0 | 0.0 |

