# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 41 / unreviewed 0 · TAKE/SKIP 9/32 (22.0% TAKE)

**Account (every call):** $1,055.89 (+5.59% on $1,000.00) · 91.6% allocated · cash $87.96

**TAKE only (the Judge's scorecard):** $899.24 (-10.08%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** -2.10% — equal weight across all 41 priced call(s)

**Generated:** 2026-10-17T23:13:48+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 41 |
| Reviewed calls | 41 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 9 |
| Shadow (SKIP) calls | 32 |
| Open | 16 |
| Right | 11 |
| Wrong | 20 |
| Neutral | 10 |
| Hit rate % | 26.8 |
| **Total PnL % (equal weight, all calls)** | -2.10% |
| Average PnL % per call | -2.1 |
| Portfolio PnL % (equal weight, TAKE only) | -10.95 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 41 | 16 | 11 | 20 | 10 | 26.8 | -2.1 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.55 |
| stock | 40 | 15 | 11 | 20 | 9 | 27.5 | -2.12 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 0 | 0 | 1 | 0.0 | -1.55 |
| momentum_breakout | 1 | 1 | 0 | 0 | 1 | 0.0 | -8.96 |
| premarket_gap | 15 | 6 | 3 | 8 | 4 | 20.0 | -10.78 |
| squeeze | 24 | 8 | 8 | 12 | 4 | 33.3 | 3.58 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 9 | 6 | 1 | 3 | 5 | 11.1 | -10.95 |
| SKIP (shadow) | 32 | 10 | 10 | 17 | 5 | 31.2 | 0.38 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -11.33 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 3.86 | 3.74 | 0.12 | -0.016 | 41 | quality (higher is better) |
| technician | 5.32 | 5.07 | 0.25 | -0.053 | 41 | quality (higher is better) |
| skeptic | 6.27 | 5.62 | 0.66 | 0.215 | 41 | severity (lower is better) |
| risk_manager | 5.59 | 5.35 | 0.24 | 0.127 | 41 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 6 | 1 | 1 | 4 | 1 | 16.7 | 11.38 |
| 40-70 | 27 | 12 | 10 | 11 | 6 | 37.0 | 2.49 |
| 70-100 | 8 | 3 | 0 | 5 | 3 | 0.0 | -27.71 |


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
| run_20261017T231339Z | 2026-10-17T23:13:39+00:00 | no | — | — | — |
| run_20261016T140541Z | 2026-10-16T14:05:41+00:00 | yes | 1 | 1 | 0.0 |
| run_20261016T125656Z | 2026-10-16T12:56:57+00:00 | yes | 1 | 0 | 0.0 |
| run_20261015T113816Z | 2026-10-15T11:38:16+00:00 | yes | 0 | 0 | 0.0 |
| run_20261015T064704Z | 2026-10-15T06:47:04+00:00 | no | 0 | 1 | 0.0 |

