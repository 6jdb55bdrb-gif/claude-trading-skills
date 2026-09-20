# Tracker schema, PnL rules and statistics

## Tables (`state/lowcap_calls.db`)

### `calls`

One row per call. `kind` is `active` (Judge said TAKE) or `shadow` (Judge said
SKIP — tracked identically so the Judge's value is measurable).

| Column | Meaning |
|---|---|
| `ticker`, `asset_type` | symbol, `stock` or `etf` |
| `direction` | `long` or `short` — from the Risk Manager |
| `kind` | `active` or `shadow` |
| `call_date`, `entry_price` | when the call was made and at what price |
| `screen_variant` | `squeeze`, `momentum_breakout`, `etf_momentum` |
| `judge_decision`, `confidence`, `judge_reason` | the Judge's output |
| `researcher_score`, `technician_score`, `skeptic_score`, `risk_manager_score` | the four role scores (skeptic = severity) |
| `stop_price`, `target_price`, `shares`, `position_usd`, `risk_usd` | the plan |
| `status` | `OPEN` or `CLOSED_WRONG` |
| `current_price`, `pnl_pct`, `last_price_at` | latest observation |
| `closed_at`, `close_reason` | set only on a stop-out |
| `run_id`, `backend`, `notes` | provenance |

A partial unique index on `ticker WHERE status = 'OPEN'` means the same ticker
can never hold two open calls; the de-duplication rule is enforced by the
database, not by application logic. Once a call closes, the ticker is eligible
again.

### `role_verdicts`

The full JSON verdict of all five roles per call (`call_id`, `role`, `score`,
`backend`, `verdict_json`). Every call keeps its complete reasoning.

### `price_history`

One row per observation (`call_id`, `observed_at`, `price`, `pnl_pct`), starting
with the entry itself.

### `runs`

One row per cycle: session reason, whether screening ran, hits, reviews, new
calls, takes, shadows, closes, prices, backend, LLM cost.

### `llm_usage`

Per role call: `run_id`, `month`, `role`, `model`, token counts and `cost_usd`.
`month_to_date_spend()` sums this table for the monthly cap.

## PnL

Direction-corrected, in percent of entry:

```
long   pnl = (current - entry) / entry * 100
short  pnl = (entry - current) / entry * 100
```

A long called at $200 that trades at $210 is +5%; a short called at $200 that
trades at $190 is also +5%.

## Closing rule

`pnl <= tracker.close_threshold_pct` (default **-80%**) closes the call as
`CLOSED_WRONG` and removes it from active tracking; it stays in the statistics
forever. **There is no other auto-close.** Winners are never taken off the books,
and a -79% call stays open. The threshold is a configuration value, not a
constant.

## Outcome labels

| Label | Condition |
|---|---|
| `RIGHT` | current PnL > 0 |
| `WRONG` | closed at the threshold |
| `NEUTRAL` | still open, PnL at or below 0 |

Hit rate = RIGHT / total calls.

## Statistics (printed every run, written to `tracker-output/stats.md`)

| Block | Contents |
|---|---|
| Overall | total, TAKE, shadow, open, right, wrong, neutral, hit rate, average PnL, best and worst call |
| Portfolio | equal-weight PnL across TAKE calls (open + closed), and across all calls |
| By direction | long vs short |
| By asset type | stock vs ETF |
| By screen variant | `squeeze`, `momentum_breakout`, `etf_momentum` |
| TAKE vs SKIP | both blocks plus the Judge edge (average TAKE PnL − average shadow PnL) and a verdict line |
| Per-role accuracy | average score among winners vs others, the edge, and Pearson correlation of score against PnL, with polarity |
| Confidence buckets | `learning.confidence_buckets` (default 0–40 / 40–70 / 70–100): count, hit rate, average PnL |
| Recent runs | last five runs with screening flag, new calls, closes and LLM cost |

**Reading the role table.** The Researcher, Technician and Risk Manager should
show a *positive* edge and correlation; the Skeptic should show a *negative* one
(low severity on winners). A role whose correlation sits near zero over enough
samples is not contributing, which is exactly what the weekly learning loop
proposes fixing.

**Reading the Judge edge.** Positive means the calls the Judge took beat the ones
it rejected. Negative, with enough samples, means the Judge is filtering out the
wrong candidates — the loop then proposes re-weighting, because the shadow calls
are the control group that makes the claim testable.

## Learning loop output

`tracker-output/improvements.md`, weekly. Numbered proposals, each with the file
or configuration key to change, the finding that triggered it, the proposed
change and an approval checkbox. `learning.min_samples` (default 10) gates every
role and Judge conclusion so a handful of calls cannot rewrite the prompts.
Nothing is ever applied automatically.
