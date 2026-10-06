# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 13 / unreviewed 0 · TAKE/SKIP 2/11 (15.4% TAKE)

**Account (every call):** $1,235.10 (+23.51% on $1,000.00) · 40.0% allocated · cash $799.16

**TAKE only (the Judge's scorecard):** $974.28 (-2.57%). What following the Judge's verdicts alone would have returned — the gap against the account above is what the Judge's selectivity is worth.

**Total PnL:** +18.08% — equal weight across all 13 priced call(s)

**Generated:** 2026-10-06T05:52:37+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 13 |
| Reviewed calls | 13 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 2 |
| Shadow (SKIP) calls | 11 |
| Open | 4 |
| Right | 5 |
| Wrong | 6 |
| Neutral | 2 |
| Hit rate % | 38.5 |
| **Total PnL % (equal weight, all calls)** | +18.08% |
| Average PnL % per call | 18.08 |
| Portfolio PnL % (equal weight, TAKE only) | -12.86 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** SDEV (long, squeeze, shadow) -36.21% — entry 7.58 → 4.835000038146973

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 13 | 4 | 5 | 6 | 2 | 38.5 | 18.08 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.03 |
| stock | 12 | 3 | 4 | 6 | 2 | 33.3 | 19.59 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| etf_momentum | 1 | 1 | 1 | 0 | 0 | 100.0 | 0.03 |
| squeeze | 12 | 3 | 4 | 6 | 2 | 33.3 | 19.59 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 2 | 1 | 0 | 1 | 1 | 0.0 | -12.86 |
| SKIP (shadow) | 11 | 3 | 5 | 5 | 1 | 45.5 | 23.71 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -36.57 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.5 | 4.75 | -0.25 | -0.188 | 13 | quality (higher is better) |
| technician | 4.1 | 4.75 | -0.65 | 0.087 | 13 | quality (higher is better) |
| skeptic | 7.9 | 7.44 | 0.46 | 0.326 | 13 | severity (lower is better) |
| risk_manager | 4.7 | 4.31 | 0.39 | 0.261 | 13 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 0 | 1 | 1 | 0 | 50.0 | 61.35 |
| 40-70 | 8 | 2 | 3 | 4 | 1 | 37.5 | 21.59 |
| 70-100 | 3 | 2 | 1 | 1 | 1 | 33.3 | -20.12 |


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
| run_20261006T055218Z | 2026-10-06T05:52:18+00:00 | no | 0 | 0 | 0.0 |
| run_20261005T195427Z | 2026-10-05T19:54:27+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T153822Z | 2026-10-05T15:38:22+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T153331Z | 2026-10-05T15:33:31+00:00 | yes | 0 | 0 | 0.0 |
| run_20261005T142600Z | 2026-10-05T14:26:00+00:00 | yes | 1 | 1 | 0.0 |

