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

## Findings added by hand — 2026-10-01, second scan

### 7. [HIGH] the "Judge is not adding value" line is not yet measuring the Judge

- **Finding:** stats.md reports `edge=-35.11 (Judge is not adding value)`. That
  number is one TAKE against nine SKIPs, and eight of those nine carry template
  text rather than reasoning: calls 1-8 all read "Skeptic objection unanswered"
  or "SKIP — Skeptic objection not explicitly answered", with the identical
  sentence produced for a Skeptic score of 4.5 (GDC) and of 10.0 (SDEV). A rule
  that fires the same way on a 4.5 and a 10.0 is not weighing anything. Note
  that the `backend` column says `llm` for calls 4-8 even so, which is exactly
  the silent-fallback problem the backend health check was added to stop — the
  column cannot be trusted for that era.
- **Consequence:** the Judge-edge figure, the per-role edges and the
  confidence-bucket table are currently descriptions of a heuristic that no
  longer runs. They should not be used to tune the Judge, and the learning
  loop's "Judge too strict?" proposal rests on the same rows.
- **Proposed change:** compute the Judge-edge and per-role statistics only over
  calls whose review carries substantive reasoning, and report the count
  alongside, so three real reviews cannot read as a verdict on the system.
- **Approve?** ☐ yes  ☐ no

### 8. [MEDIUM] SDEV is the one name the template gate rejected, twice

- **Finding:** SDEV was SKIPped at 1.04 (+175.8%, the book's best call) and again
  at 3.20 (+31.2% open). Both times the stated reason was an unanswered Skeptic
  objection; both times the Skeptic score was 9.0-10.0. Every other call the
  same gate rejected lost money, so the gate is 5-for-7 — but the two it missed
  are the only two calls that made anything.
- **Reading, stated carefully:** the gated group averages +21.2%, and that whole
  number is SDEV. The median of the group is -13.5%. This is not evidence that
  the gate is backwards; it is evidence that a blanket objection rule cannot
  distinguish the one setup worth taking from five that were not.
- **Proposed change:** when the role review is live again, check whether a high
  Skeptic score on a *dilution* objection behaves differently from one on an
  *extension* objection. SDEV's was dilution both times.
- **Approve?** ☐ yes  ☐ no

### 9. [MEDIUM] what the wider trail costs per position

- **Finding:** with the ATR trail live, the stop on a fresh call sits far below
  entry until the price rises. Today's book:

  | | entry | trail | stop at | locked in |
  |---|---|---|---|---|
  | SDEV | 3.20 | 20.2% | 3.39 | **+5.9%** |
  | VEEA | 3.20 | 40.3% | 1.97 | -38.4% |
  | MEDS | 4.30 | 37.7% | 2.68 | -37.7% |

  SDEV has risen enough that its trail now protects a gain. VEEA and MEDS each
  risk about 38% of the slice before the stop engages — $38 of a $100 slice,
  which is 3.8% of the $1,000 account per position, or roughly 11% across three.
  That is the accepted cost of not being stopped out by noise, and it is larger
  than the old fixed 15% made it look.
- **Proposed change:** none yet — this is the agreed trade-off, recorded so the
  account-level risk is visible. If three or four wide-ATR positions open at
  once, consider scaling the slice down by the trail width so each call risks a
  similar number of dollars rather than a similar number of dollars of notional.
- **Approve?** ☐ yes  ☐ no

## Findings added by hand — 2026-10-01, third scan

### 10. [HIGH] the two dead variants, diagnosed against the live screener

Three consecutive scans have returned the same three tickers. Probing each
variant's filters one token at a time, live, settles why.

**`momentum_breakout` — 0 hits, and redundant rather than merely broken.**
`ta_highlow52w_nh` (at a new 52-week high) is the binding token: dropping it
takes the variant from 0 hits to 3. But those 3 are **SDEV, VEEA, MEDS** — the
identical set `squeeze` already returns. Every other token in the variant
(cap, price band, relvol, above SMA20/50, float, US-only) is a subset of the
squeeze filters, so the 52-week high was the *only* thing distinguishing the
two. Fixing it does not widen the funnel; it clones it.

| token dropped | hits |
|---|---|
| `ta_highlow52w_nh` | 3 — `SDEV, VEEA, MEDS` (same as squeeze) |
| `sh_float_u20` | 1 |
| `sh_avgvol_o500` | 1 |
| anything else | 0 |

**`etf_momentum` — 0 hits; fixable, but into a different strategy.**
Same binding token: dropping `ta_highlow52w_nh` gives 5 hits — `COHH, AXTL,
DXD, TETH, RWM`. DXD and RWM are *inverse* index ETFs (short Dow, short Russell
2000). So the variant can be made to fire, but what it returns is leveraged and
inverse index products at a new high — a market-hedging signal, not a lowcap
squeeze. As written it does not belong in this skill.

**The root contradiction:** this strategy screens microcaps that are 80-95%
below their 52-week highs for short squeezes. Two of the three variants
simultaneously require a *new 52-week high*. The premises cannot both hold, so
the variants were unfireable from the day they were written, not broken later.

**What actually limits `squeeze`,** measured the same way — and note that the
cheap-looking knobs do nothing:

| change | hits |
|---|---|
| as shipped (`sh_float_u20`, `sh_short_o15`) | 3 — `SDEV, VEEA, MEDS` |
| `sh_float_u50` | 3 — unchanged |
| `sh_float_u100` | 5 — `+ VUZI, GO` |
| no float filter | 6 — `+ PACB` |
| no float, `sh_short_o10` | 8 |
| no float, no short-float floor | 14 |
| market cap up to mid, float u50, short o20 | 3 — unchanged |

Widening short float or market cap changes nothing. The float cap is the only
knob that adds names while leaving the thesis intact, and the short-float floor
*is* the thesis — removing it is not widening the screen, it is abandoning the
premise the whole book is built on.

- **Options, in order of cost:**
  1. `sh_float_u20` → `sh_float_u100` on `squeeze`: 3 → 5-6 names a day, thesis
     untouched. The cheapest real improvement.
  2. Delete `momentum_breakout`. Fixing it duplicates `squeeze`; it cannot earn
     its place without being re-specified around a genuinely different setup
     (a pullback-continuation entry, say, rather than a breakout).
  3. Drop `etf_momentum` from this skill, or re-scope it explicitly as a
     market-hedging screen and judge it on different criteria.
  4. `sh_short_o15` → `sh_short_o10`: 8 names, but a weaker squeeze premise.
     Not recommended without a reason to believe 10-15% short float squeezes.
- **Approve?** ☐ 1  ☐ 2  ☐ 3  ☐ 4  ☐ none
