# Tracker schema, PnL rules and statistics

## Tables (`state/lowcap_calls.db`)

### `calls`

One row per call. `kind` is `active` (Judge said TAKE) or `shadow` (Judge said
SKIP — tracked identically so the Judge's value is measurable).

| Column | Meaning |
|---|---|
| `ticker`, `asset_type` | symbol, `stock` or `etf` |
| `direction` | PnL convention: `long` for a call, `short` for a put |
| `instrument` | `call` or `put` — what is actually traded |
| `expiry_date` | the contract's expiration (a Friday); closing it is the only close rule |
| `strike` | nearest strike to the money on the side the trade needs |
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

### `subscribers`

One row per chat with access: `chat_id` (primary key), `display_name`, `role`
(`admin` / `member`), `status` (`active` / `removed` / `banned` / `blocked`),
`joined_at`, `left_at`, `invited_by` and the `invite_code` redeemed. Only
`active` rows receive broadcasts; a removed row is kept so a rejoin, a ban or a
block stays on the record.

### `invites`

One row per invite code: `code` (primary key), `created_at`, `created_by`,
`max_uses`, `uses`, `expires_at`, `revoked_at` and an optional `note`. A code is
usable while it is un-revoked, un-expired and `uses < max_uses`; redemption
increments `uses` in the same transaction that creates the subscriber.

Both tables are exported to `tracker.members_file` (default
`state/lowcap_members.json`, which git ignores) rather than to the committed
`tracker-output/state_snapshot.json`. A scheduled run on a throwaway checkout
keeps its calls and PnL from the public snapshot; codes and chat ids stay off
the public record.

## PnL

Direction-corrected, in percent of entry:

```
long   pnl = (current - entry) / entry * 100
short  pnl = (entry - current) / entry * 100
```

A long called at $200 that trades at $210 is +5%; a short called at $200 that
trades at $190 is also +5%.

## Closing rule

A call is an option, so it closes when **its contract expires** — status
`EXPIRED`, settled at the underlying's last known price. Nothing else closes it:
a 90% drawdown keeps running, because the contract still has time to recover.

`tracker.close_threshold_pct` is null by default; set a negative number to
re-enable the old early stop-out (status `CLOSED_WRONG`) alongside expiry.
Setting `close_on_expiry: false` with no threshold is rejected at load time —
some close rule must exist.

**PnL is measured on the underlying**, not on an option premium: the screened
universe (low float, $1-20) has no listed options, so no premium can be quoted.
The contract is recorded; the percentage is the stock's move, direction-corrected
(a put gains when the underlying falls).

## Outcome labels

| Label | Condition |
|---|---|
| `RIGHT` | expired above the entry, or open and currently up |
| `WRONG` | expired at or below the entry (or stopped out, when a threshold is set) |
| `NEUTRAL` | open and not up — the contract still has time |

Hit rate = RIGHT / total calls.

## Statistics (printed every run, written to `tracker-output/stats.md`)

| Block | Contents |
|---|---|
| Overall | total, TAKE, shadow, open, right, wrong, neutral, hit rate, average PnL, best and worst call |
| Portfolio | equal-weight PnL across TAKE calls (open + closed), and across all calls |
| By instrument | call vs put |
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
