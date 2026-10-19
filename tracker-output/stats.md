# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 42 / unreviewed 0 · TAKE/SKIP 9/33 (21.4% TAKE)

**Account (every call):** $1,084.09 (+8.41% on $1,000.00) · 84.0% allocated · cash $166.35

**TAKE only (the Judge's scorecard):** $914.15 (-8.59%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -1.56% — equal weight across all 42 priced call(s)

**Generated:** 2026-10-19T18:21:47+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 42 |
| Reviewed calls | 42 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 9 |
| Shadow (SKIP) calls | 33 |
| Open | 15 |
| Right | 13 |
| Wrong | 21 |
| Neutral | 8 |
| Hit rate % | 31.0 |
| **Total PnL % (equal weight, all calls)** | -1.56% |
| Average PnL % per call | -1.56 |
| Portfolio PnL % (equal weight, TAKE only) | -9.38 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 42 | 15 | 13 | 21 | 8 | 31.0 | -1.56 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.85 |
| stock | 41 | 14 | 13 | 21 | 7 | 31.7 | -1.55 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.85 |
| momentum_breakout | 1 | 1 | 0 | 0 | 1 | 0.0 | -4.49 |
| premarket_gap | 15 | 5 | 4 | 8 | 3 | 26.7 | -9.73 |
| squeeze | 25 | 8 | 9 | 13 | 3 | 36.0 | 3.47 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 9 | 4 | 2 | 4 | 3 | 22.2 | -9.38 |
| SKIP (shadow) | 33 | 11 | 11 | 17 | 5 | 33.3 | 0.57 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -9.95 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.84 | 3.73 | 0.1 | -0.01 | 42 | quality (higher is better) |
| technician | 5.35 | 5.07 | 0.28 | -0.05 | 42 | quality (higher is better) |
| skeptic | 6.04 | 5.74 | 0.3 | 0.202 | 42 | severity (lower is better) |
| risk_manager | 5.69 | 5.34 | 0.35 | 0.127 | 42 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 10.89 |
| 40-70 | 28 | 11 | 11 | 12 | 5 | 39.3 | 2.28 |
| 70-100 | 8 | 3 | 1 | 5 | 2 | 12.5 | -24.35 |


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
| run_20261019T182115Z | 2026-10-19T18:21:15+00:00 | yes | — | — | — |
| run_20261019T145622Z | 2026-10-19T14:56:22+00:00 | yes | 1 | 1 | 0.0 |
| run_20261019T144714Z | 2026-10-19T14:47:14+00:00 | yes | 0 | 0 | 0.0 |
| run_20261017T231339Z | 2026-10-17T23:13:39+00:00 | no | 0 | 0 | 0.0 |
| run_20261016T140541Z | 2026-10-16T14:05:41+00:00 | yes | 1 | 1 | 0.0 |

