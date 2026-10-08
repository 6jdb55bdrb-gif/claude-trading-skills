# Screener versions: v1 → v2

Two generations of filters live side by side in `assets/tracker_config.yaml`
under `screener.versions`. `screener.screener_version` picks the standing one;
`run_cycle.py --screener-version v2` runs the other for a single cycle without
touching what a scheduled run screens. Every logged call records the version
that produced it (`calls.screener_version`), so the comparison is settled on
outcomes rather than on opinion.

The live default is **v1**. Flipping it changes what the live book screens and
brings in v2's run gate; that is a deliberate edit, not a side effect.

## Why v2 exists

v1 ran for weeks and produced almost nothing. The diagnosis, filter by filter:

| v1 filter | What it did | What it cost |
|---|---|---|
| `sh_short_o15` (squeeze) | hard floor at 15% short float | FinViz refreshes short interest **twice a month**. A stale number excluded live squeezes and admitted names whose shorts had already covered. A hard filter on stale data is the worst of both. |
| `sh_float_u20` (both) | float under 20M shares | Excluded the mid-float names that squeeze hardest, and most of the liquid end of the universe. |
| `sh_relvol_o3` (breakout) | relative volume over 3x | 3x is already a gap-and-go; by the time it prints, the move is mostly done. |
| `ta_highlow52w_nh` (breakout) | new 52-week high only | A single-session condition, and the one session where a name is most extended. Fired approximately never. |
| `sh_avgvol_o500` (squeeze) | 500k average volume | On a sub-$20 lowcap this cuts a large part of the intended universe. |

## The changes

### squeeze

| | v1 | v2 |
|---|---|---|
| float | `sh_float_u20` | `sh_float_u50` |
| average volume | `sh_avgvol_o500` | `sh_avgvol_o300` |
| relative volume | `sh_relvol_o2` | `sh_relvol_o2` |
| short float | `sh_short_o15` (hard filter) | **removed** — scored instead |
| order | `-relativevolume` | `-relativevolume` |

### momentum_breakout

| | v1 | v2 |
|---|---|---|
| 52-week position | `ta_highlow52w_nh` (new high) | `ta_highlow52w_b0to5h` (within 5% of the high) |
| float | `sh_float_u20` | **removed** |
| relative volume | `sh_relvol_o3` | `sh_relvol_o2` |
| order | `-change` | `-relativevolume` |

If v2's `momentum_breakout` still produces zero calls after 5 trading days, the
report flags it for deletion (`flag_for_deletion_after_days: 5`). A variant that
never fires is not conservative, it is decoration.

### etf_momentum

Removed from v2 entirely. It stays in v1, and v1's calls for it stay
explainable: `find_variant_spec` searches every version, so a report can quote a
retired variant's filters.

## What replaced the hard filters

A FinViz filter can only ever narrow a screen, so everything v2 stopped
rejecting is now **weighed** after the fetch (`scripts/screener_guards.py`):

- **Change cap** (`guards.max_change_pct: 25.0`). A name already up more than
  +25% on the day is skipped: that is a chase, not an entry. The cap reads one
  side only — a name down 40% is not capped — and a missing change column keeps
  the name, because a data gap is not evidence. Every skip is named in the run
  report and in the Telegram message.
- **Short-float bonus** (`guards.short_float_bonus`). +5 confidence at ≥10%
  short float, +10 at ≥20%, read from the ownership view. Only the top matching
  rung pays. It is applied **before** the Judge's gate, so a crowded short can
  carry a name over `min_confidence_to_take` — which is the point of replacing
  a filter with a score. It moves the number only; the gate alone decides TAKE
  vs SKIP.
- **Run gate** (`earliest_run: 08:00 Europe/Zurich`). The operator's own floor
  on when a scan may screen. 08:00 Zurich is 02:00 ET, before the pre-market
  tape opens, so in practice the market's extended-hours window (04:00 ET) is
  the binding constraint. An earlier run logs the skip and **still prices the
  open book**: skipping the stop checks would be the more expensive failure.
  (This replaced a 16:30 floor whose job — keeping relative volume off a
  partial session — now belongs to the per-variant `sessions` list below.)

### Session-aware variants

Each v2 variant declares the session phases it is valid in, and `screen_all`
only runs the ones that match the current phase:

| Variant | Sessions | Why |
|---|---|---|
| `squeeze` | regular, afterhours | ranks on relative volume and "up today", neither of which exists before the open |
| `momentum_breakout` | regular, afterhours | same |
| `premarket_gap` | premarket | a gap is only a gap before the open |

v1's variants declare nothing and keep running in every phase: the generation
is frozen.

### The pre-market screen

FinViz's public screener has **no pre-market filter**. Measured 2026-10-08
mid-session: `order=-premarketchange` is silently ignored and falls back to
ticker order (the same trap as an unrecognised filter token — a bogus token
returns the unfiltered universe, so validity has to be proven by narrowing,
never by the absence of an error). `ta_perf_dup`, `sh_relvol_o2` and
`ta_change_u5` are real tokens, but before the open they read the previous
session.

So the pre-market screen splits the job:

1. **FinViz gives the universe** — market cap, price, float, average volume,
   country, stocks-only. Structural facts that do not change overnight. No
   filter here may depend on today's tape.
2. **The universe is capped** (`max_universe: 60`), most-traded first, because
   measuring costs one tape request per name and a pre-market scan slower than
   the pre-market session is useless. Liquidity is the right thing to keep: a
   gap on an empty book is one order, not demand.
3. **The gap is measured from the tape** (one batched yfinance prepost
   download) and the name must clear `min_gap_pct: 5.0` **and**
   `min_volume_pct_of_adv: 10.0`. These sit below the explosion-signal
   premarket bonus (+10% on 20% of ADV) on purpose: this is the bar to be
   looked at, not the bar to score.
4. **The measured print becomes the entry price**, with the previous close kept
   as `prior_close` — a pre-market call entered at yesterday's close is priced
   at a level nobody can get. The measured gap also becomes the hit's
   `change_pct`, so the +25% chase cap reads the pre-market move rather than
   yesterday's change.

A name with no pre-market print is dropped silently: most of the universe has
none, and reporting it would bury the real skips.

## Explosion signals (v2 only)

Runs on every surviving hit **after** the FinViz filters and **before** the
Judge, so all five roles argue about the same measured sheet. Every value is
passed to the Researcher, Skeptic and Judge, stored on the call
(`calls.signals_json`, `calls.signal_bonus`), and the key ones ride along in
the Telegram message. v1 has no signals layer.

Two rules run through the whole thing:

- **A source that failed is not evidence.** Each signal reports `ok` (it
  looked; here is what it found) or `n/a` (it could not look). An `n/a` scores
  nothing. Collapsing the two would make "EDGAR was unreachable"
  indistinguishable from "this company has filed nothing", and those lead to
  opposite decisions.
- **Signals rank setups; they do not manufacture them.** Hence the cap, and
  hence the hard skips that no score can outvote.

### Bonuses

| Signal | Rule | Points | Source |
|---|---|---|---|
| Float rotation | today's volume ÷ float ≥ 0.5× / ≥ 1.0× | +5 / +10 | screener row |
| Catalyst recency | 8-K, 8-K/A, 6-K or news inside 24h | +10 | EDGAR, FinViz tape |
| — no catalyst | looked, found nothing | **−15** | EDGAR, FinViz tape |
| Squeeze pressure | days to cover ≥ 3 **or** borrow fee ≥ 20% | +5 | FinViz short ratio, iBorrowDesk |
| Volatility contraction | 10-session range in the bottom 20% of 60 sessions **and** RelVol ≥ 2 | +10 | yfinance daily |
| Premarket gap | gap ≥ 10% **and** premarket volume ≥ 20% of ADV | +5 | yfinance prepost |
| VWAP position | at or above VWAP / below it | +5 / **−10** | yfinance intraday |
| Insider buying | Form 4 open-market purchase inside 30 days | +5 | EDGAR |
| Thin institutions | institutional ownership < 20% | +3 | screener row (ownership view) |
| Sector sympathy | ≥ 2 other names in the industry up > 10% today | +5 | one FinViz movers screen per cycle |

The **cap is +30 on the layer's net effect**, and only on the upside. Every
signal firing at once is +58, which would carry a 20-confidence setup over any
threshold. There is deliberately no floor: the VWAP charge and the
missing-catalyst charge are the layer's whole point on a weak sheet, and a
signal sheet is allowed to argue a name down as far as it likes. A charge that
was netted off still appears per-signal — "signals +30" hiding a VWAP failure
inside it is the kind of number that gets a call bought.

In v2 the catalyst signal **replaces** `roles.judge.no_catalyst_penalty`: the
charge is made once, here, against the filing and news record rather than
against a role's opinion of it. v1 keeps the role-level penalty it was measured
with. Both never fire together.

### Hard skips

The Judge returns SKIP and names the filter. Checked for every hit, before the
confidence test, and not outvotable by a perfect score:

| Filter | Rule | Source |
|---|---|---|
| Dilution | S-3, S-1, 424B3/4/5, F-3 (or amendments) inside 90 days | EDGAR |
| Reverse split | split ratio < 1 inside 180 days | yfinance splits |
| Cash runway | cash ÷ (quarterly operating burn ÷ 3) < 6 months | EDGAR XBRL |
| Repeated halts | more than 2 halts in today's session | Nasdaq Trader feed |

**Missing data never skips.** A hard skip is an accusation, and an unreachable
source does not get to make one.

### SEC fair access

EDGAR needs no key, but it has conditions: a declared User-Agent naming a real
contact, and at most 10 requests/second. Both are enforced in `edgar_client`:

- **With no User-Agent the client sends nothing at all** — not "sends and
  fails". An anonymous request is a policy breach even when it would work, and
  a tracker that quietly breached it would get the operator's IP blocked
  mid-run. Every EDGAR-backed signal then reports `n/a`.
- A User-Agent without an `@` is refused too: `python-requests` is exactly what
  the policy exists to stop.
- One rate limiter sits in front of every request (config asks for 8/second),
  and the ticker map is cached per run instead of re-fetched per hit.

Turn the EDGAR signals on with one line:

```yaml
screener:
  versions:
    v2:
      explosion_signals:
        edgar:
          user_agent: "lowcap-tracker you@example.com"
```

or `export EDGAR_USER_AGENT="lowcap-tracker you@example.com"`.

### Source availability, measured 2026-10-07

| Source | Status here |
|---|---|
| yfinance intraday (VWAP, premarket) | working |
| yfinance daily (range percentile) | working |
| yfinance splits (reverse split) | working |
| Nasdaq Trader halt feed | working |
| FinViz movers screen (sympathy) | working |
| SEC EDGAR | reachable (HTTP 200), **awaiting a configured contact** |
| iBorrowDesk | **HTTP 403 from this host** — borrow fee reports n/a; days-to-cover still covers the signal |

### Which signals actually work

`outcome_report.py` scores each signal the same way it scores the versions:
the calls it fired on against the calls it did not, with the edge between
them. Calls carrying no sheet at all (every v1 call) are in neither column —
counting them as "without" would credit each signal with v1's whole record.
After 30 calls the table says which signals to keep.

## The fixed stop

`tracker.sl_pct: 20.0` and `scripts/stop_loss.py`:

```
calculate_stop_loss(entry_price) == round(entry_price * (1 - sl_pct / 100), 2)
```

Resolved at insert time against the entry actually stored, written to
`calls.sl_price` for TAKEs and shadow SKIPs alike, and printed on every call
line in the Telegram message. It is distinct from `trail_pct`: the trailing stop
moves with the peak, this line never moves. `sl_pct: null` disables it rather
than falling back to an invented default. Long only — `roles.allow_short` stays
false, and a short has no stop line because the formula subtracts from entry.

## Outcome tracking

`scripts/outcome_tracker.py` measures every call, TAKE and SKIP:

- returns at **+1, +3 and +5 sessions** after the call. The call's own session
  is day zero: the entry is the price at scan, so that day's close is already a
  result. Horizons count sessions, so weekends and holidays do not consume one.
- each session's **low** is checked against `sl_price`, because a stop is hit
  intraday, not at the close. A low equal to the stop counts as a hit.
- a stopped call is **out at the stop**: horizons that elapsed before it keep
  their real closes, the horizon it fired in and every later one record the
  stop's return, and no price after the stop is read again.
- the current session's bar is never used — mid-session its close is not a
  close, and a wrong +1d return would never be revisited.
- a call with no elapsed horizon is pending, not a loss.

`scripts/outcome_report.py` scores it: hit rate, average return and stop-hit
rate per version, per variant and per confidence bucket (`<50`, `50-59`,
`60-69`, `70+`), plus the Judge's own edge (TAKE average minus SKIP average).
It enters the Telegram summary once **30 measured calls** exist.

The report **recommends and never applies**. `min_confidence_to_take` and
`no_catalyst_penalty` are the two dials that decide what gets traded; a loop
that moved them on its own would be optimising against a few weeks of noise.
A threshold proposal is raised only to just above the highest band that has
actually lost money — never over an unmeasured band — and only when a higher
band has been shown to pay. Both proposals require at least 5 calls in each
slice and carry `applied: false`.

## Commands

```bash
# One v2 cycle without changing the standing version
python3 scripts/run_cycle.py --screener-version v2

# What v2 would ask FinViz for
python3 scripts/screener_variants.py --urls   # reads screener.screener_version

# Measure outcomes, then score v1 against v2
python3 scripts/outcome_tracker.py --fill --verbose
python3 scripts/outcome_report.py --fill
```
