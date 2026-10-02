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

## Findings added by hand — 2026-10-01, fourth scan

### 11. [INFO] entry timing is NOT biased toward the day's high — hypothesis rejected

All three open calls faded from their morning highs, which looked like it might
mean the screener systematically buys the top of the day. Tested: for every
call, where the entry sat inside that call's own regular-session range, where
0% is the day's low and 100% the day's high.

| call | date | entry | day low | day high | in range |
|---|---|---|---|---|---|
| GDC | 09-21 | 1.76 | 1.33 | 1.95 | 69% |
| GRML | 09-22 | 10.67 | 12.61 | 18.21 | **-35%** |
| MSS | 09-23 | 1.93 | 1.81 | 2.95 | 11% |
| NCPL | 09-24 | 1.27 | 1.20 | 1.63 | 16% |
| MEDS | 09-28 | 3.91 | 3.44 | 4.65 | 39% |
| SDEV | 10-01 | 3.20 | 3.48 | 4.54 | **-26%** |
| MEDS | 10-01 | 5.16 | 3.63 | 4.35 | **213%** |
| VEEA | 10-01 | 3.20 | 2.92 | 3.93 | 28% |
| MEDS | 10-01 | 4.30 | 3.63 | 4.35 | 93% |

**Mean 45%, against a neutral 50%. Three of nine in the top third.** The
hypothesis does not hold: the fading is this universe's behaviour, not an entry
timing bias, and no fix is warranted. The negative result is recorded so the
question is not re-opened on a hunch.

The outliers are informative, though. `213%` is the MEDS 5.16 pre-market entry
(finding 5) — quantified, it was taken above the *entire* regular-session range
of the day it was bought in. The two negative figures are the opposite case:
GRML and SDEV were bought pre-market *below* the regular session's eventual low,
which is a better price than the session ever offered.

**This weakens my own finding 5, and the operator's decision to keep pre-market
screening looks better than my write-up implied.** Splitting the book by
session:

| | n | sum | avg | median |
|---|---|---|---|---|
| regular hours | 6 | +113.5% | +18.9% | -10.1% |
| pre / post | 4 | -7.8% | -2.0% | -2.2% |

Regular hours wins on the mean only because SDEV +175.8% sits in it; strip that
and regular hours averages **-12.5%**, worse than pre-market. By median
pre-market is ahead. With 10 calls none of this is significant, and it should
not be treated as such — but there is no evidence here for restricting
pre-market entries. The narrow concern in finding 5 stands: a *zero-volume*
quote at the top of a thin spike is a bad entry, and that is one call, not a
session-wide rule.

- **Proposed change:** none. Finding 5 should be read as being about the single
  MEDS 5.16 entry rather than about pre-market trading in general.

## Findings added by hand — 2026-10-02, overnight scan

### 12. [HIGH] the high-water mark is the highest price a SCAN SAMPLED, not the session's high

`peak_price` is documented as "the highest price seen since entry". What it
actually holds is the highest price a scan happened to observe. The tracker
reads a price when it runs, so any move between runs is invisible to it.

Measured on the 1 October close:

| | tracker's peak | true session high | understated by |
|---|---|---|---|
| SDEV | 4.24 | **4.54** | 7.1% |
| VEEA | 3.47 | **4.08** | 17.6% |
| MEDS | 4.30 | 4.35 | 1.1% |

Because the trail measures from that mark, every stop is looser than the
configured distance implies. SDEV's 20.2% trail should have sat at 3.62 and
actually sat at 3.39.

**That difference decided the position.** SDEV's low after its high was 3.40:

| peak used | trail | stop | outcome |
|---|---|---|---|
| sampled 4.24 | 20.2% (ATR) | 3.39 | **survived** — closed 3.65, +14.1% |
| true 4.54 | 20.2% (ATR) | 3.62 | stopped ~+13.2% |
| sampled 4.24 | 15% (old) | 3.60 | stopped ~+12.6% |
| true 4.54 | 15% (old) | 3.86 | stopped **~+20.6%** |

**This is evidence against the ATR widening I recommended and that was
approved.** The best exit available on this call was the *old, tighter* stop
measured from the *correct* high: +20.6%, better than the +14.1% the position is
actually worth. The combination that ran — an understated peak with a widened
trail — gave the worst of the three exits that banked a gain. One call is not a
refutation of the 6-call replay that argued for the widening, and it is not
presented as one, but it points the other way and should be recorded as such
rather than smoothed over.

**Implemented:** `tracker.peak_from_session_high`, with the session High now
fetched alongside the close and the peak ratcheting on it when the flag is set.
The mark only ever rises, a missing High degrades to the sampled price, and a
High below entry cannot lower the mark.

**Left `false`,** so no stop tightens under an operator who has not asked for
it. Flipping it on today closes nothing, but changes the room to each stop:

| | now | stop (sampled peak) | room | stop (true high) | room |
|---|---|---|---|---|---|
| SDEV | 3.66 | 3.39 | +8.0% | 3.62 | **+1.0%** |
| VEEA | 3.47 | 2.07 | +67.5% | 2.44 | +42.5% |
| MEDS | 4.06 | 2.68 | +51.6% | 2.71 | +49.8% |

- **Decision needed:** `true` gives the trailing stop its ordinary meaning and
  the distance you actually configured. `false` keeps today's accidentally
  looser behaviour. The honest summary is that the one data point available
  favours a tighter stop on a correct high, and the replay favoured a wider one
  on an understated high; those are not the same comparison, and 6 closed calls
  cannot separate them.
- **Approve?** ☐ true  ☐ keep false

## Findings added by hand — 2026-10-02, operator query

### 13. [CRITICAL] the account value funded calls the system said to SKIP

Raised by the operator: the account figure did not match the PnL they believed
they had. They were right, and it was worse than a display problem.

`portfolio_state` funded **every** call at a full $100 slice — the nine the
Judge rejected as well as the one it took. So the headline "PORTFOLIO
$1,115.73 (+11.57%)" was the return of a portfolio that bought all ten screener
hits, nine of which the system had explicitly said not to buy.

Decomposed:

| | n | $ effect |
|---|---|---|
| TAKE — what the system recommended | 1 | **-18.99** |
| SKIP — what it told you not to buy | 9 | **+134.71** |
| total shown as "the account" | 10 | +115.72 |

The entire gain came from SKIPs, and almost all of it from one: SDEV at 1.04,
which the Judge rejected and which then ran +175.8%. The only call the system
actually recommended lost money.

**Following the system was worth $981.01, or -1.90%.** Not +11.57%.

Two further consequences of funding both from one pot:

* **Cash was fiction.** "cash $798.49" was the balance of a book that had
  bought nine names it declined. The real account never spent anything beyond
  the one TAKE.
* **A stretch of SKIPs could starve a real TAKE.** Shadow allocations drew down
  the same cash, so ten SKIPs would leave the next genuine TAKE with a fraction
  of a slice, or nothing.

**Fixed.** Two books, each honest about what it is:

* `portfolio_state` — **the account**: TAKE calls only, and only a TAKE spends
  cash. Reads `$981.01 (-1.90%)`.
* `shadow_state` — **the screener's book**: every call at a notional slice, so
  the Judge's selectivity can still be priced. Reads `$1,115.73 (+11.57%)`,
  labelled in both reports as not an account.

A voided call is in neither. An UNREVIEWED call is in the shadow book only —
nobody decided to take it, so the account cannot have funded it.

This also makes the Judge's record concrete rather than a statistic: its one
TAKE lost 19.0% while its SKIPs averaged +15.0%. On ten calls that is not
significant, but it is no longer hidden inside a flattering account number.

## Findings added by hand — 2026-10-02, 06:02 ET scan

### 14. [HIGH] a mark from yesterday's session was printed as "now"

At 06:02 ET on Friday the book read `SDEV now=3.66 pnl=+14.4%`. SDEV was
trading **5.21** in pre-market at that moment, a session high of 5.52, and
**+62.8%** from the 3.20 entry. The same run's screener saw it: `SDEV price=5.22
chg=42.61`.

Nothing was mis-priced. The tracker marks on completed daily bars, and no daily
bar exists for 2 October until the session makes one, so holding Thursday's
close is the correct answer. Printing it as `now` with no label is not, and it
is the same class of error as pricing a call on a bar that predates it: the
report stated something it did not know.

**Fixed.** A mark whose bar predates the current *Eastern* date is tagged
`PRIOR CLOSE (<date>)`. The tag appends rather than replaces, so a stop-out or
expiry stays the louder fact without losing which session the mark came from.
`prior_session_marks` lists the affected tickers on the result. The day is the
market's, not the server's.

Two of my own tests were wrong before this passed, both in the same way: they
fed a bar older than the call, which the pre-entry guard correctly refuses, so
the call went unpriced and the new flag never set. The prior-close case only
arises once a call has outlived the session it was made in — which is every
call, by the next day.

**The consequence that is not fixed, and matters more:** the trailing stop and
the high-water mark both run on these daily marks. SDEV's recorded peak is
4.24, Thursday's intraday high was 4.54, and it has now printed 5.52
pre-market. The 20.2% trail therefore sits at 3.39 — around **39% below where
the stock is actually trading**. A position can run a long way and give most of
it back before a stop measured from a stale peak notices. That is finding 12
(`peak_from_session_high`, still set `false`) seen from the other side, and it
is now costing the book its largest open gain rather than protecting it.

- **Proposed change:** none beyond the tag, which is a truth fix. The real
  decision is finding 12. Note what it is now worth: on the live book, a peak
  that tracked the session high would have the SDEV stop near 4.40 rather than
  3.39.
