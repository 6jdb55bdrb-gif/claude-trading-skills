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
- **Run gate** (`earliest_run: 16:30 Europe/Zurich`). v2 orders by relative
  volume, and in the first hour after the US open that ratio compares a partial
  session against a full one — it ranks whatever opened first, not whatever is
  unusual. An earlier run logs the skip and **still prices the open book**:
  skipping the stop checks would be the more expensive failure.

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
