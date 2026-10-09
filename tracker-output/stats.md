# Lowcap Call Tracker — Statistics

**Backend:** UP · reviewed 19 / unreviewed 0 · TAKE/SKIP 5/14 (26.3% TAKE)

**Account (every call):** $1,173.20 (+17.32% on $1,000.00) · 80.0% allocated · cash $326.31

**TAKE only (the Judge's scorecard):** $968.39 (-3.16%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +9.12% — equal weight across all 19 priced call(s)

**Generated:** 2026-10-09T07:34:02+00:00<br>
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
| Right | 8 |
| Wrong | 8 |
| Neutral | 3 |
| Hit rate % | 42.1 |
| **Total PnL % (equal weight, all calls)** | +9.12% |
| Average PnL % per call | 9.12 |
| Portfolio PnL % (equal weight, TAKE only) | -6.32 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -56.46% — entry 4.57 → 1.9900000095367432

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 19 | 8 | 8 | 8 | 3 | 42.1 | 9.12 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| stock | 18 | 7 | 7 | 8 | 3 | 38.9 | 9.61 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.16 |
| squeeze | 18 | 7 | 7 | 8 | 3 | 38.9 | 9.61 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 5 | 3 | 2 | 2 | 1 | 40.0 | -6.32 |
| SKIP (shadow) | 14 | 5 | 6 | 6 | 2 | 42.9 | 14.63 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -20.95 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.41 | 4.36 | 0.05 | -0.04 | 19 | quality (higher is better) |
| technician | 4.81 | 5.0 | -0.19 | 0.022 | 19 | quality (higher is better) |
| skeptic | 6.0 | 7.09 | -1.09 | 0.164 | 19 | severity (lower is better) |
| risk_manager | 5.44 | 4.41 | 1.03 | 0.214 | 19 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 12 | 5 | 6 | 5 | 1 | 50.0 | 14.23 |
| 70-100 | 5 | 3 | 1 | 2 | 2 | 20.0 | -24.05 |


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
| run_20261009T073355Z | 2026-10-09T07:33:56+00:00 | no | — | — | — |
| run_20261008T175505Z | 2026-10-08T17:55:05+00:00 | yes | 0 | 0 | 0.0 |
| run_20261008T171310Z | 2026-10-08T17:13:10+00:00 | yes | 3 | 1 | 0.0 |
| run_20261008T125555Z | 2026-10-08T12:55:56+00:00 | no | 0 | 0 | 0.0 |
| run_20261008T091406Z | 2026-10-08T09:14:06+00:00 | no | 0 | 0 | 0.0 |
