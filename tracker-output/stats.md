# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 42 / unreviewed 0 · TAKE/SKIP 9/33 (21.4% TAKE)

**Account (every call):** $1,073.32 (+7.33% on $1,000.00) · 91.9% allocated · cash $85.33

**TAKE only (the Judge's scorecard):** $911.40 (-8.86%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -1.78% — equal weight across all 42 priced call(s)

**Generated:** 2026-10-19T14:56:58+00:00<br>
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
| Open | 16 |
| Right | 12 |
| Wrong | 20 |
| Neutral | 10 |
| Hit rate % | 28.6 |
| **Total PnL % (equal weight, all calls)** | -1.78% |
| Average PnL % per call | -1.78 |
| Portfolio PnL % (equal weight, TAKE only) | -9.69 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 42 | 16 | 12 | 20 | 10 | 28.6 | -1.78 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.72 |
| stock | 41 | 15 | 12 | 20 | 9 | 29.3 | -1.78 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.72 |
| momentum_breakout | 1 | 1 | 0 | 0 | 1 | 0.0 | -5.24 |
| premarket_gap | 15 | 5 | 4 | 8 | 3 | 26.7 | -10.04 |
| squeeze | 25 | 9 | 8 | 12 | 5 | 32.0 | 3.32 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 9 | 5 | 2 | 3 | 4 | 22.2 | -9.69 |
| SKIP (shadow) | 33 | 11 | 10 | 17 | 6 | 30.3 | 0.38 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -10.07 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.88 | 3.72 | 0.15 | -0.011 | 42 | quality (higher is better) |
| technician | 5.29 | 5.1 | 0.19 | -0.052 | 42 | quality (higher is better) |
| skeptic | 5.92 | 5.8 | 0.12 | 0.206 | 42 | severity (lower is better) |
| risk_manager | 5.58 | 5.4 | 0.18 | 0.125 | 42 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 11.03 |
| 40-70 | 28 | 12 | 10 | 11 | 7 | 35.7 | 2.14 |
| 70-100 | 8 | 3 | 1 | 5 | 2 | 12.5 | -25.1 |


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
| run_20261019T145622Z | 2026-10-19T14:56:22+00:00 | yes | — | — | — |
| run_20261019T144714Z | 2026-10-19T14:47:14+00:00 | yes | 0 | 0 | 0.0 |
| run_20261017T231339Z | 2026-10-17T23:13:39+00:00 | no | 0 | 0 | 0.0 |
| run_20261016T140541Z | 2026-10-16T14:05:41+00:00 | yes | 1 | 1 | 0.0 |
| run_20261016T125656Z | 2026-10-16T12:56:57+00:00 | yes | 1 | 0 | 0.0 |

