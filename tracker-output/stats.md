# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 11 / unreviewed 0 · TAKE/SKIP 2/9 (18.2% TAKE)

**Account (TAKE calls only):** $972.95 (-2.70% on $1,000.00) · 10.0% allocated · cash $881.01

**Shadow book (every hit, SKIPs included):** $1,213.82 (+21.38%). This is what the screener surfaced, not an account — nobody would have bought the SKIPs.

**Total PnL:** +19.44% — equal weight across all 11 priced call(s)

**Generated:** 2026-10-05T09:39:24+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 11 |
| Reviewed calls | 11 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 2 |
| Shadow (SKIP) calls | 9 |
| Open | 4 |
| Right | 4 |
| Wrong | 5 |
| Neutral | 2 |
| Hit rate % | 36.4 |
| **Total PnL % (equal weight, all calls)** | +19.44% |
| Average PnL % per call | 19.44 |
| Portfolio PnL % (equal weight, TAKE only) | -13.53 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 11 | 4 | 4 | 5 | 2 | 36.4 | 19.44 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 11 | 4 | 4 | 5 | 2 | 36.4 | 19.44 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 11 | 4 | 4 | 5 | 2 | 36.4 | 19.44 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 2 | 1 | 0 | 1 | 1 | 0.0 | -13.53 |
| SKIP (shadow) | 9 | 3 | 4 | 4 | 1 | 44.4 | 26.76 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -40.29 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.88 | 5.14 | -0.27 | -0.423 | 11 | quality (higher is better) |
| technician | 4.88 | 5.07 | -0.2 | -0.207 | 11 | quality (higher is better) |
| skeptic | 8.12 | 7.14 | 0.98 | 0.574 | 11 | severity (lower is better) |
| risk_manager | 4.88 | 4.71 | 0.16 | 0.169 | 11 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 1 | 1 | 1 | 0 | 50.0 | 59.79 |
| 40-70 | 8 | 2 | 3 | 4 | 1 | 37.5 | 13.58 |
| 70-100 | 1 | 1 | 0 | 0 | 1 | 0.0 | -14.42 |


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
| run_20261005T093900Z | 2026-10-05T09:39:00+00:00 | yes | — | — | — |
| run_20261005T074121Z | 2026-10-05T07:41:21+00:00 | no | 0 | 0 | 0.0 |
| run_20261004T212408Z | 2026-10-04T21:24:08+00:00 | no | 0 | 0 | 0.0 |
| run_20261002T192937Z | 2026-10-02T19:29:37+00:00 | yes | 0 | 0 | 0.0 |
| run_20261002T153210Z | 2026-10-02T15:32:10+00:00 | yes | 1 | 0 | 0.0 |

