# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 19 / unreviewed 0 · TAKE/SKIP 5/14 (26.3% TAKE)

**Account (every call):** $1,115.75 (+11.58% on $1,000.00) · 80.0% allocated · cash $326.31

**TAKE only (the Judge's scorecard):** $967.83 (-3.22%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +6.09% — equal weight across all 19 priced call(s)

**Generated:** 2026-10-08T17:13:37+00:00<br>
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 19 |
| Reviewed calls | 19 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 5 |
| Shadow (SKIP) calls | 14 |
| Open | 8 |
| Right | 6 |
| Wrong | 8 |
| Neutral | 5 |
| Hit rate % | 31.6 |
| **Total PnL % (equal weight, all calls)** | +6.09% |
| Average PnL % per call | 6.09 |
| Portfolio PnL % (equal weight, TAKE only) | -6.44 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 19 | 8 | 6 | 8 | 5 | 31.6 | 6.09 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.05 |
| stock | 18 | 7 | 5 | 8 | 5 | 27.8 | 6.43 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.05 |
| squeeze | 18 | 7 | 5 | 8 | 5 | 27.8 | 6.43 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 1 | 2 | 2 | 20.0 | -6.44 |
| SKIP (shadow) | 14 | 5 | 5 | 6 | 3 | 35.7 | 10.57 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -17.0 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.33 | 0.17 | -0.11 | 19 | quality (higher is better) |
| technician | 4.42 | 5.15 | -0.74 | -0.069 | 19 | quality (higher is better) |
| skeptic | 6.92 | 6.5 | 0.42 | 0.207 | 19 | severity (lower is better) |
| risk_manager | 5.25 | 4.65 | 0.6 | 0.231 | 19 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 12 | 5 | 4 | 5 | 3 | 33.3 | 9.01 |
| 70-100 | 5 | 3 | 1 | 2 | 2 | 20.0 | -23.01 |


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
| run_20261008T171310Z | 2026-10-08T17:13:10+00:00 | yes | — | — | — |
| run_20261008T125555Z | 2026-10-08T12:55:56+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T091406Z | 2026-10-08T09:14:06+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T083305Z | 2026-10-08T08:33:05+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T083011Z | 2026-10-08T08:30:11+00:00 | no | 0 | 0 | 0.0 |
