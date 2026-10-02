# Lowcap Call Tracker — Statistics

> ## ⛔ BACKEND DOWN
>
> The role review could not run: None.
> New screener hits are recorded UNREVIEWED and will be judged on the
> next healthy run. No decision below was made while the backend was down.

**Backend:** DOWN · reviewed 10 / unreviewed 0 · TAKE/SKIP 1/9 (10.0% TAKE)

**Account (TAKE calls only):** $981.01 (-1.90% on $1,000.00) · 0.0% allocated · cash $981.01

**Shadow book (every hit, SKIPs included):** $1,115.73 (+11.57%). This is what the screener surfaced, not an account — nobody would have bought the SKIPs.

**Total PnL:** +11.57% — equal weight across all 10 priced call(s)

**Generated:** 2026-10-02T08:18:18+00:00  
**Close rule:** contracts run to expiry

## Overall

| Metric | Value |
|---|---|
| Total calls | 10 |
| Reviewed calls | 10 |
| UNREVIEWED calls | 0 |
| Voided (not executable) | 2 |
| TAKE calls | 1 |
| Shadow (SKIP) calls | 9 |
| Open | 3 |
| Right | 4 |
| Wrong | 5 |
| Neutral | 1 |
| Hit rate % | 40.0 |
| **Total PnL % (equal weight, all calls)** | +11.57% |
| Average PnL % per call | 11.57 |
| Portfolio PnL % (equal weight, TAKE only) | -18.99 |

**Best call:** SDEV (long, squeeze, shadow) +175.82% — entry 1.04 → 2.868499994277954
**Worst call:** GDC (long, squeeze, shadow) -25.52% — entry 1.76 → 1.3107999563217163

### By instrument (call / put)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| call | 10 | 3 | 4 | 5 | 1 | 40.0 | 11.57 |

### By asset type

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| stock | 10 | 3 | 4 | 5 | 1 | 40.0 | 11.57 |

### By screen variant

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| squeeze | 10 | 3 | 4 | 5 | 1 | 40.0 | 11.57 |

### TAKE vs SKIP (is the Judge adding value?)

| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| TAKE | 1 | 0 | 0 | 1 | 0 | 0.0 | -18.99 |
| SKIP (shadow) | 9 | 3 | 4 | 4 | 1 | 44.4 | 14.97 |

**Judge edge (avg PnL TAKE − avg PnL shadow):** -33.96 → Judge is not adding value

### Per-role accuracy

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n | Polarity |
|---|---|---|---|---|---|---|
| researcher | 4.88 | 5.17 | -0.29 | -0.118 | 10 | quality (higher is better) |
| technician | 4.88 | 4.75 | 0.12 | 0.187 | 10 | quality (higher is better) |
| skeptic | 8.12 | 7.33 | 0.79 | 0.366 | 10 | severity (lower is better) |
| risk_manager | 4.88 | 4.25 | 0.62 | 0.62 | 10 | quality (higher is better) |

### Confidence buckets


| Group | Calls | Open | Right | Wrong | Neutral | Hit rate % | Avg PnL % |
|---|---|---|---|---|---|---|---|
| 0-40 | 2 | 1 | 1 | 1 | 0 | 50.0 | 0.1 |
| 40-70 | 7 | 1 | 3 | 4 | 0 | 42.9 | 17.3 |
| 70-100 | 1 | 1 | 0 | 0 | 1 | 0.0 | -5.58 |


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
| run_20261002T080618Z | 2026-10-02T08:06:18+00:00 | yes | 0 | 0 | 0.0 |
| run_20261002T045403Z | 2026-10-02T04:54:03+00:00 | no | 0 | 0 | 0.0 |
| run_20261001T173437Z | 2026-10-01T17:34:37+00:00 | yes | 0 | 0 | 0.0 |
| run_20261001T150019Z | 2026-10-01T15:00:19+00:00 | yes | 0 | 0 | 0.0 |
| run_20261001T143713Z | 2026-10-01T14:37:13+00:00 | yes | 0 | 0 | 0.0 |

