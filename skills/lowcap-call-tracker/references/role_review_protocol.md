# Role review protocol

Every screener hit passes through five roles before it can become a call. The
prompts are the single source of truth and live in `agents/lowcap-*.md`: Claude
Code loads them as subagents, and `role_review.py` sends the same file bodies as
system prompts to the Anthropic API. There is no second copy to drift.

## The roles

| Role | Question | Model tier | Reuses |
|---|---|---|---|
| RESEARCHER | Why is it moving, and will the reason last? | worker | `stockbee-episodic-pivot-analyzer`, web search |
| TECHNICIAN | Is the chart tradable right now? | worker | `technical-analyst` (`weekly_price_action`) |
| SKEPTIC | What is the strongest reason not to? | worker | — |
| RISK MANAGER | Long or short, what stop, what size? | worker | `position-sizer` |
| JUDGE | TAKE or SKIP, and how sure? | judge | reads the other four |

Default models: `claude-haiku-4-5` for the four analysts, `claude-sonnet-5` for
the Judge (`roles.models`).

## Score polarity — the one thing to get right

| Role | 0 means | 10 means |
|---|---|---|
| RESEARCHER | no catalyst found | hard, dated, company-changing catalyst |
| TECHNICIAN | parabolic / no definable support | clean trend, tight breakout, modest extension |
| **SKEPTIC** | **nothing disqualifying found** | **disqualifying on its own** |
| RISK MANAGER | no viable plan | tight structural stop with a clean 3R path |

The Skeptic's score is **objection severity**: it is subtracted in the blend
(`roles.weights.skeptic`), reported with `polarity: severity (lower is better)` in
the statistics, and the learning loop expects a *negative* correlation with PnL
from it.

## Verdict schemas

All five return a single JSON object. Required keys:

```
researcher   role score catalyst_type catalyst_summary catalyst_date sector_theme
             insider_buying evidence[] reasons[]
technician   role score trend support resistance volume_pattern
             extension_pct_sma20 breakout_quality reasons[]
skeptic      role score strongest_objection objection_category risk_flags[]
             what_would_change_my_mind reasons[]
risk_manager role score direction direction_reason entry stop stop_basis target
             r_multiple_to_target shares position_usd risk_usd
             position_pct_of_account reasons[]
judge        role decision confidence reason skeptic_objections_answered
             skeptic_answer key_risk reasons[]
```

`_normalize_verdict` coerces whatever the model returns: scores clamp to 0–10,
confidence to an integer 0–100, `decision` to exactly TAKE or SKIP, `direction`
to long / short / none, and `reasons` to a list of at most three strings. A
response that is not parseable JSON is treated as an unavailable role and the
deterministic backend answers instead.

## The Judge gate (enforced in code)

`enforce_judge_gate` runs after the Judge, on both backends, and overturns a TAKE
when any of these hold:

1. `risk_manager.direction == "none"` — there is no executable plan.
2. `skeptic_objections_answered` is false, or `skeptic_answer` is shorter than 20
   characters (a token acknowledgement is not a rebuttal), while
   `roles.judge.require_skeptic_answer` is true.
3. `confidence < roles.judge.min_confidence_to_take` (default 55).

Overturned decisions keep a `gate_overrides` list, and the call is stored as a
shadow call — so a model that inflates confidence or waves an objection away is
visible in the statistics rather than silently trading.

## Backends

| Backend | When | Behaviour |
|---|---|---|
| `llm` | `ANTHROPIC_API_KEY` set and the monthly cap has room | Messages API per role |
| `heuristic` | no key, no SDK, cap reached, or `--backend heuristic` | deterministic scoring from screener fields and adapter output |
| `auto` | default | LLM when available, heuristic per role on any failure (the failure is recorded in the review's `notes`) |

The heuristic backend is not a stub: it applies the same rules the prompts
describe (extension penalties, dilution flags at sub-$1.50, ETF-specific
objections, structural stops capped at 20% of price), which is what makes the dry
run, the tests and the cap fallback meaningful.

Model parameters are chosen per model family: Haiku 4.5 rejects adaptive thinking
and `effort`, so worker calls send neither; the Judge's model gets
`thinking: {"type": "adaptive"}` and `output_config.effort`.

## Cost model

Every call's token usage is priced from `llm.prices_per_mtok` and written to the
`llm_usage` table with its run id, role and model. Two controls:

- **Per-run logging** — the run output prints cost, token counts and
  month-to-date spend against the cap.
- **Monthly cap** — `llm.monthly_spend_cap_usd` (default $10). When
  month-to-date spend reaches it, `LLMClient.available()` returns false and the
  roles fall back to the heuristic backend. No run is ever aborted for budget.

A five-role review of one candidate is roughly 3–5K input and 1–2K output tokens,
so a handful of new candidates per run costs single-digit cents.

## Reuse adapters

`skill_adapters.py` calls the sibling skills. Each is best-effort: a failure
returns an `error` string that lands in the review's `notes`, and the role falls
back to the screener fields. Nothing in the adapter layer can abort a run.

| Adapter | Skill | Feeds |
|---|---|---|
| `run_episodic_pivot` | `stockbee-episodic-pivot-analyzer` | catalyst type, EP type, composite score, component scores |
| `run_weekly_price_action` | `technical-analyst` | weekly verdict, confidence, swing levels |
| `run_position_sizer` | `position-sizer` | shares, position value, risk dollars, binding constraint |
| `fetch_daily_bars` | yfinance | daily OHLCV for the two adapters above |

## Backends, and what is never faked

`roles.llm_only` (default: RESEARCHER, SKEPTIC, JUDGE) lists the roles that must
come from the LLM or not at all. If one of them cannot be answered,
`review_hit` raises `ReviewUnavailable` and the caller records the hit as
UNREVIEWED rather than substituting a deterministic verdict.

TECHNICIAN and RISK MANAGER keep their offline implementations on purpose: they
are arithmetic on the screener row (extension from the moving averages, a stop,
a position size, a strike and an expiry). Computing those offline is honest;
inventing a catalyst, an objection or a verdict is not.

| Failure | What happens |
|---|---|
| `anthropic` not installed | health check fails at the `availability` stage |
| `ANTHROPIC_API_KEY` unset | health check fails at the `availability` stage |
| bad key, no credit, network blocked | health check fails at the `request` stage |
| monthly cap reached | health check fails at the `availability` stage |
| one role returns JSON that cannot be parsed | `ReviewUnavailable` for that hit only |

## The catalyst penalty

`none_found` is a minus, not a veto. When the Researcher scores below
`roles.judge.catalyst_score_floor`, `apply_catalyst_penalty` deducts
`roles.judge.no_catalyst_penalty` confidence points and records what it did in
`judge_verdict["catalyst_penalty"]`. The usual confidence threshold then applies
to what is left, so a strong enough setup survives a thin news tape and a
mediocre one does not.

The Skeptic gate is unchanged: an objection must still be answered explicitly.
But "the Researcher found no catalyst" is not an unanswerable objection — it is
answered with the structure, the stop and the risk actually being relied on.

## Long only

`roles.allow_short` is false. These low-float names have no listed options and
no reliable borrow, so a bearish call could never have been taken — and an
inexecutable position in the record collects PnL nobody could have had.

Enforcement is layered, so no backend can route around it:

1. The RISK MANAGER prompt tells the model to return `instrument: "none"` for a
   bearish setup rather than a put.
2. `_normalize_verdict` neutralizes any `put` / `short` that arrives anyway,
   setting `short_suppressed: true` and recording why in `reasons`. It does
   **not** flip the plan to a long: the setup was bearish, and inventing a
   bullish thesis nobody argued would be worse than skipping.
3. The Judge gate turns a plan with no direction into a SKIP.
4. `insert_call(allow_short=False)` raises rather than storing a put.

A put already on the book keeps its own PnL convention — history is not
rewritten. Set `roles.allow_short: true` only if the universe moves to
optionable, borrowable names.
