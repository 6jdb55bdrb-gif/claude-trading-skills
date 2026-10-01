# Lowcap Call Tracker — Proposed Improvements

**Generated:** 2026-10-01T13:57:12+00:00  
**Window:** last 90 days — 12 calls, 12 priced  
**Minimum samples before a conclusion:** 10

> Nothing here is applied automatically. Each item names the file or config key to change; approve the ones you want and edit them yourself (or ask Claude to apply a specific numbered item).

## Evidence

| Role | Avg score (winners) | Avg score (others) | Edge | Corr(score, PnL) | n |
|---|---|---|---|---|---|
| researcher | 4.33 | 5.36 | -1.02 | -0.154 | 10 |
| technician | 4.0 | 5.14 | -1.14 | 0.132 | 10 |
| skeptic | 9.0 | 7.07 | 1.93 | 0.408 | 10 |
| risk_manager | 5.0 | 4.29 | 0.71 | 0.591 | 10 |

| Variant | Calls | Hit rate % | Avg PnL % |
|---|---|---|---|
| squeeze | 10 | 30.0 | 11.91 |

**Judge edge (TAKE − shadow avg PnL):** -34.34 (Judge is not adding value)

## Proposals

### 1. [MEDIUM] role prompt — `agents/lowcap-researcher.md`

- **Finding:** researcher score does not separate winners from losers (edge -1.02, corr -0.154 over 10 calls; positive correlation expected)
- **Proposed change:** Tighten the researcher scoring rubric: add a worked example for the 3-6 band, and require the score to cite a specific field (catalyst date, extension %, dollar volume) rather than a judgement word.
- **Approve?** ☐ yes  ☐ no

### 2. [MEDIUM] role prompt — `agents/lowcap-skeptic.md`

- **Finding:** skeptic score does not separate winners from losers (edge 1.93, corr 0.408 over 10 calls; negative correlation expected)
- **Proposed change:** Tighten the skeptic scoring rubric: add a worked example for the 3-6 band, and require the score to cite a specific field (catalyst date, extension %, dollar volume) rather than a judgement word.
- **Approve?** ☐ yes  ☐ no

### 3. [MEDIUM] screener filters — `screener.variants.squeeze.filters`

- **Finding:** variant 'squeeze': 10 calls, hit rate 30.0%, avg PnL 11.91%
- **Proposed change:** Tighten the squeeze universe: raise short float to `sh_short_o20`, require `sh_relvol_o3`, and consider `sh_price_o2` to leave the most dilution-prone band. Current filters: cap_smallunder,sh_price_1to20,sh_avgvol_o500,sh_relvol_o2,ta_perf_dup,ta_sma20_pa,ta_sma50_pa,ind_stocksonly,geo_usa,sh_float_u20,sh_short_o15
- **Approve?** ☐ yes  ☐ no

### 4. [HIGH] judge policy — `agents/lowcap-judge.md`

- **Finding:** Judge too strict? 10 of the last 11 reviewed calls were SKIP (90.9%), above the 90.0% alarm line.
- **Proposed change:** Read the stored judge_reason of the recent SKIPs and find which rule is doing the skipping. If it is the confidence floor, consider lowering roles.judge.min_confidence_to_take (now 55). If it is the Skeptic gate, tighten the Skeptic prompt so a generic 'low float stocks are risky' is not scored as disqualifying. If it is the catalyst penalty, review roles.judge.no_catalyst_penalty. Nothing here is applied automatically.
- **Approve?** ☐ yes  ☐ no


## Findings added by hand — 2026-10-01 scan

These two came out of the 1 October cycle and are not produced by the
automated loop. Neither is applied: both change risk policy, which is the
operator's call.

### 5. [HIGH] entry window — `market.extended_open`

- **Finding:** MEDS was called at 5.16 at 06:18 ET on 2026-10-01, from a
  pre-market quote taken at the top of a 06:10 spike to 5.44. Every
  pre-market 5-minute bar that session reported **zero volume** — these are
  quote-derived prints, not trades. The regular session then opened at 3.92.
  The trailing stop fired on the fade and booked a realized -19.0%.
  The price data was correct; the entry was not executable. This is the same
  failure class as pricing a call on a bar that predates it, in the other
  direction.
- **Proposed change:** Either restrict new calls to regular hours
  (09:30-16:00 ET), or keep pre-market screening but defer the entry price to
  the regular-session open. Do not keep booking entries at zero-volume
  pre-market quotes on sub-$20M microcaps.
- **Decision (2026-10-01):** *not now* — pre-market screening stays on, and
  pre-market quotes continue to set the entry. The finding stands as the
  explanation for the MEDS 5.16 entry and its -19.0% exit; revisit if a
  second call is entered on a zero-volume print.

### 6. [HIGH] stop geometry — `tracker.trailing_stop_pct`

- **Finding:** the fixed 15% trail is narrower than one day's range on most of
  this universe. 6 of 10 calls had ATR above 13% of entry; 4 were above 22%
  (MEDS 28.9%, VEEA 26.9%, MEDS 25.1%, MEDS 22.5%). A 15% trail inside a 27%
  ATR closes on noise rather than on thesis failure. Replaying the whole book
  on daily closes against a `max(15%, 1.5 x ATR%)` trail:

  | | fixed 15% | 1.5x ATR |
  |---|---|---|
  | sum over 10 calls | +92.0% | +117.1% |
  | avg per call | +9.2% | +11.7% |
  | MEDS 3.91 | -18.9% | +6.1% (still open) |
  | NCPL 1.27 | -15.0% | -3.1% (still open) |
  | GRML 10.67 | +11.1% | -2.8% |

  The trade-off is real and visible in GRML: a wider trail cuts fewer losers
  at noise but surrenders more open profit on a name that round-trips.
- **Caveats, stated plainly:** 6 closed calls is not a sample. One name (SDEV
  +149%) supplies all of the profit under both rules, and both rules captured
  it identically, so the comparison rests on 5 calls. The replay walks daily
  closes, while the live tracker samples whenever a scan runs, so it is an
  approximation of the live rule rather than a backtest of it.
- **Proposed change:** scale the trail to volatility —
  `max(15%, 1.5 x ATR/entry)` — rather than fixing it at 15%. Consider
  pairing it with a tightening rule once a call is up enough that giving back
  a GRML-sized gain is the larger risk.
- **Approve?** ☐ yes  ☐ no
- **Decision (2026-10-01): APPLIED.** `trailing_stop_atr_mult: 1.5` added, with
  `trailing_stop_pct: 15.0` kept as the floor. The distance is resolved once at
  entry from the ATR on the screener row and stored per call (`calls.trail_pct`),
  so changing the setting never re-stops a position that is already open, and a
  book keeps the geometry it was taken with. The floor remains the single
  off-switch: `trailing_stop_pct: null` disables the trail entirely, and the
  multiplier only ever widens a trail that is switched on. Closed calls were
  left closed — their stops fired under the rule in force at the time, and
  re-opening banked results would rewrite the record.
