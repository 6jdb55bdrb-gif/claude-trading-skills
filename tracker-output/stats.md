# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 43 / unreviewed 0 · TAKE/SKIP 9/34 (20.9% TAKE)

**Account (every call):** $1,077.76 (+7.78% on $1,000.00) · 93.6% allocated · cash $66.35

**TAKE only (the Judge's scorecard):** $913.33 (-8.67%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -1.72% — equal weight across all 43 priced call(s)

**Generated:** 2026-10-20T09:20:36+00:00<br>
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
| Open | 16 |
| Right | 13 |
| Wrong | 21 |
| Neutral | 9 |
| Hit rate % | 30.2 |
| **Total PnL % (equal weight, all calls)** | -1.72% |
| Average PnL % per call | -1.72 |
| Portfolio PnL % (equal weight, TAKE only) | -9.47 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 43 | 16 | 13 | 21 | 9 | 30.2 | -1.72 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.88 |
| stock | 42 | 15 | 13 | 21 | 8 | 31.0 | -1.72 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.88 |
| momentum_breakout | 1 | 1 | 0 | 0 | 1 | 0.0 | -4.32 |
| premarket_gap | 16 | 6 | 4 | 8 | 4 | 25.0 | -9.25 |
| squeeze | 25 | 8 | 9 | 13 | 3 | 36.0 | 3.2 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 9 | 4 | 3 | 4 | 2 | 33.3 | -9.47 |
| SKIP (shadow) | 34 | 12 | 10 | 17 | 7 | 29.4 | 0.33 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -9.8 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.92 | 3.67 | 0.26 | -0.007 | 43 | quality (higher is better) |
| technician | 5.35 | 5.07 | 0.28 | -0.053 | 43 | quality (higher is better) |
| skeptic | 5.62 | 5.97 | -0.35 | 0.2 | 43 | severity (lower is better) |
| risk_manager | 5.77 | 5.32 | 0.45 | 0.123 | 43 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 11.15 |
| 40-70 | 29 | 12 | 11 | 12 | 6 | 37.9 | 1.91 |
| 70-100 | 8 | 3 | 1 | 5 | 2 | 12.5 | -24.56 |


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
| run_20261020T092000Z | 2026-10-20T09:20:00+00:00 | yes | — | — | — |
| run_20261019T182115Z | 2026-10-19T18:21:15+00:00 | yes | 0 | 1 | 0.0 |
| run_20261019T145622Z | 2026-10-19T14:56:22+00:00 | yes | 1 | 1 | 0.0 |
| run_20261019T144714Z | 2026-10-19T14:47:14+00:00 | yes | 0 | 0 | 0.0 |
| run_20261017T231339Z | 2026-10-17T23:13:39+00:00 | no | 0 | 0 | 0.0 |

