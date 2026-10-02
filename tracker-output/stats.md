# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: the 'anthropic' package is not installed.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 11 / unreviewed 0 · TAKE/SKIP 2/9 (18.2% TAKE)

**Account (TAKE calls only):** $977.71 (-2.23% on $1,000.00) · 10.0% allocated · cash $881.01

**Shadow book (every hit, SKIPs included):** $1,195.12 (+19.51%). This is what the screener surfaced, not an account — nobody would have bought the SKIPs.

**Total PnL:** +17.74% — equal weight across all 11 priced call(s)

**Generated:** 2026-10-02T19:30:03+00:00  
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
| **Total PnL % (equal weight, all calls)** | +17.74% |
| Average PnL % per call | 17.74 |
| Portfolio PnL % (equal weight, TAKE only) | -11.15 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 11 | 4 | 4 | 5 | 2 | 36.4 | 17.74 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 11 | 4 | 4 | 5 | 2 | 36.4 | 17.74 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 11 | 4 | 4 | 5 | 2 | 36.4 | 17.74 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 2 | 1 | 0 | 1 | 1 | 0.0 | -11.15 |
| SKIP (shadow) | 9 | 3 | 4 | 4 | 1 | 44.4 | 24.16 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -35.3 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.88 | 5.14 | -0.27 | -0.388 | 11 | quality (higher is better) |
| technician | 4.88 | 5.07 | -0.2 | -0.157 | 11 | quality (higher is better) |
| skeptic | 8.12 | 7.14 | 0.98 | 0.553 | 11 | severity (lower is better) |
| risk_manager | 4.88 | 4.71 | 0.16 | 0.235 | 11 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 1 | 1 | 1 | 0 | 50.0 | 49.94 |
| 40-70 | 8 | 2 | 3 | 4 | 1 | 37.5 | 13.9 |
| 70-100 | 1 | 1 | 0 | 0 | 1 | 0.0 | -16.01 |


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
| run_20261002T192937Z | 2026-10-02T19:29:37+00:00 | yes | — | — | — |
| run_20261002T153210Z | 2026-10-02T15:32:10+00:00 | yes | 1 | 0 | 0.0 |
| run_20261002T131550Z | 2026-10-02T13:15:50+00:00 | yes | 0 | 0 | 0.0 |
| run_20261002T121432Z | 2026-10-02T12:14:32+00:00 | yes | 0 | 0 | 0.0 |
| run_20261002T100707Z | 2026-10-02T10:07:07+00:00 | yes | 0 | 0 | 0.0 |

