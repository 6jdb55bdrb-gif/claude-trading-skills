---
name: lowcap-call-tracker
description: Screen US low-cap stocks and ETFs for explosive moves, run every hit through a five-role review (Researcher, Technician, Skeptic, Risk Manager, Judge), and track the resulting calls and shadow calls in SQLite with PnL, hit rate and per-role accuracy. Use when the user asks for low-float / short-squeeze / momentum-breakout screening, wants candidates argued over before they become calls, wants to track whether their calls were right, wants run summaries and call statistics pushed to Telegram, or wants the tracker deployed on a VPS to run every 4 hours.
---

# Lowcap Call Tracker

## Overview

Three FinViz screener variants find explosive candidates in the US low-cap
universe; a five-role review argues each hit before it becomes a call; a SQLite
tracker scores every call — including the ones the Judge rejected — so the whole
pipeline is measurable.

**Pipeline:** screen → five-role review → TAKE / SKIP → track → statistics →
weekly proposals.

Reused skills (never re-implemented):

| Piece | Reused skill |
|---|---|
| Filter codes, URL construction | `finviz-screener` |
| Catalyst classification and scoring | `stockbee-episodic-pivot-analyzer` |
| Weekly trend / swing levels | `technical-analyst` (`weekly_price_action`) |
| Share count, risk budget, concentration caps | `position-sizer` |
| Role prompts as Claude Code subagents | `agents/lowcap-*.md` |

---

## When to Use This Skill

**Explicit triggers:**
- "Screen for low-float short-squeeze candidates"
- "Find US low caps and ETFs with explosive potential"
- "Run the role review on these tickers"
- "Should I take this trade? Ask the Skeptic"
- "How are my calls doing?" / "What's my hit rate?"
- "Was skipping that one right?"
- "Deploy the tracker on my VPS"

**When NOT to use:**
- S&P 500 / large-cap screening (use `vcp-screener`, `canslim-screener`)
- Dividend or value screening (use `value-dividend-screener`, `kanchi-dividend-sop`)
- Position-level thesis lifecycle management (use `trader-memory-core`)
- Post-trade forensics on a closed trade (use `signal-postmortem`)

---

## Workflow

### Step 1: Review the screener variants

```bash
python3 skills/lowcap-call-tracker/scripts/screener_variants.py --urls
```

Three variants, all US-listed, price $1–$20, average volume over 500K, up today,
above the SMA20 and SMA50:

| Variant | Asset | Adds |
|---|---|---|
| `squeeze` | stocks | market cap under $2B, float under 20M, short float over 15%, RelVol over 2 |
| `momentum_breakout` | stocks | market cap under $2B, float under 20M, new 52-week high, RelVol over 3 |
| `etf_momentum` | ETFs | new 52-week high, RelVol over 2 — no float, short-float or market-cap filter |

Read `references/screener_variants.md` for the full filter-code tables, the ETF
data-gap rationale and the OTC-exclusion options.

### Step 2: Fetch hits

```bash
# Elite CSV export when FINVIZ_API_KEY is set; public HTML otherwise
python3 skills/lowcap-call-tracker/scripts/fetch_screener.py --variant squeeze

# Offline / dry run
python3 skills/lowcap-call-tracker/scripts/fetch_screener.py \
  --fixture skills/lowcap-call-tracker/scripts/fixtures/dry_run_hits.json
```

### Step 3: Run the five-role review

```bash
python3 skills/lowcap-call-tracker/scripts/role_review.py \
  --fixture skills/lowcap-call-tracker/scripts/fixtures/dry_run_hits.json --backend heuristic
```

Each role returns a JSON verdict with a 0–10 score and 2–3 reasons; the Judge
returns TAKE or SKIP with 0–100 confidence and one line of reasoning. Read
`references/role_review_protocol.md` for the verdict schemas, the Skeptic's
inverted polarity and the hard gate the code enforces.

In Claude Code the same prompts are available as subagents: `lowcap-researcher`,
`lowcap-technician`, `lowcap-skeptic`, `lowcap-risk-manager`, `lowcap-judge`.

### Step 4: Run a full cycle

```bash
# Production cycle: price open calls, screen, review, save, print + write stats
python3 skills/lowcap-call-tracker/scripts/run_cycle.py

# Dry run — no database writes, full role output
python3 skills/lowcap-call-tracker/scripts/run_cycle.py --dry-run --verbose \
  --backend heuristic --fixture skills/lowcap-call-tracker/scripts/fixtures/dry_run_hits.json \
  --force-screen
```

Order inside a cycle: session check → price update for existing open calls
(always, weekends included) → screening and review (trading days only) → new
calls → statistics.

### Step 5: Read the statistics

```bash
python3 skills/lowcap-call-tracker/scripts/stats.py --write
```

Totals, hit rate, average and extreme PnL, equal-weight portfolio PnL over TAKE
calls, breakdowns by direction / asset type / variant, TAKE vs SKIP (does the
Judge add value?), per-role accuracy and confidence-bucket hit rates. Written to
`tracker-output/stats.md`.

### Step 6: Weekly learning loop (proposals only)

```bash
python3 skills/lowcap-call-tracker/scripts/learning_loop.py --write
```

Writes `tracker-output/improvements.md` with numbered, approvable proposals for
role prompts, screener filters and Judge weighting. **Nothing is applied
automatically** — apply an item only when the user approves it.

### Step 7: Telegram (optional)

```bash
python3 skills/lowcap-call-tracker/scripts/telegram_bot.py --setup-profile  # publish the command menu
python3 skills/lowcap-call-tracker/scripts/telegram_bot.py --list-chats  # find a chat/group id
python3 skills/lowcap-call-tracker/scripts/telegram_bot.py --test       # check the wiring
python3 skills/lowcap-call-tracker/scripts/telegram_bot.py --poll       # answer commands
```

With `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` set, every run pushes a summary
(new calls with the Judge's decision, open-call PnL, closes, statistics, LLM
cost) and the weekly loop pushes its proposals. The command bot answers
`/stats`, `/open`, `/calls`, `/shadow`, `/last` from the configured chat only.
Read `references/telegram_bot.md` for the authorization rules, the message
contract and the polling model.

### Step 8: Deploy (optional)

`deploy/VPS_SETUP.md` is a step-by-step guide for a non-coder: create an Ubuntu
24.04 VPS, SSH in, run `deploy/setup_vps.sh`, check the timers, read the logs.
The systemd timer runs every 4 hours, survives reboots, rotates its logs, and
pushes `stats.md` / `improvements.md` back to GitHub.

---

## Decision Rules

- **A TAKE requires an answered objection.** The Judge must name the Skeptic's
  strongest objection and rebut it; `enforce_judge_gate` overturns any TAKE that
  does not, whatever the model returned.
- **No plan, no call.** `direction: "none"` from the Risk Manager is always SKIP.
- **A SKIP is still tracked.** Every SKIP becomes a shadow call, priced and scored
  like a real one, so the Judge's selectivity is measurable.
- **One open call per ticker.** Enforced by a partial unique index in SQLite.
- **One auto-close rule.** PnL at or below `tracker.close_threshold_pct`
  (default **-80%**) closes the call as WRONG. Nothing else auto-closes; winners
  are never taken off the books.
- **Outcome labels:** RIGHT = current PnL > 0, WRONG = closed at the threshold,
  NEUTRAL = open and at or below 0.
- **PnL is direction-corrected:** long `(now − entry) / entry`, short
  `(entry − now) / entry`.
- **Weekends and holidays skip screening, never the price update.**
- **A failing Telegram bot never fails a run.** Notification errors are caught
  and reported in the run output; the database, statistics and git push proceed.
- **Only the configured chat can command the bot.** Every other chat gets a
  refusal; `/run` additionally requires `telegram.allow_run_command`.
- **The monthly LLM cap is hard.** At `llm.monthly_spend_cap_usd` the roles fall
  back to deterministic scoring instead of spending more.

---

## Configuration

Everything tunable lives in `assets/tracker_config.yaml`; pass a partial
override document with `--config` and it is deep-merged over the default.

| Key | Default | Meaning |
|---|---|---|
| `tracker.close_threshold_pct` | -80.0 | the only auto-close rule |
| `tracker.account_size` / `risk_pct` | 10000 / 1.0 | inputs for the position sizer |
| `tracker.max_new_calls_per_run` | 10 | safety valve per cycle |
| `tracker.snapshot_file` | null | JSON state snapshot for throwaway checkouts |
| `screener.mode` | auto | elite / public / fixture |
| `screener.exchange_mode` | auto | explicit / universe / per_exchange (OTC exclusion) |
| `roles.models.worker` | claude-haiku-4-5 | Researcher / Technician / Skeptic / Risk Manager |
| `roles.models.judge` | claude-sonnet-5 | Judge |
| `roles.judge.min_confidence_to_take` | 55 | below this a TAKE becomes a shadow call |
| `llm.monthly_spend_cap_usd` | 10.0 | hard ceiling, then heuristic backend |
| `telegram.enabled` | true | master switch (still needs a token) |
| `telegram.notify_when` | changes | `changes` or `always` |
| `telegram.allow_run_command` | false | `/run` from the phone |
| `market.skip_screening_when_closed` | true | weekend / holiday behaviour |

---

## Environment

| Variable | Needed for |
|---|---|
| `ANTHROPIC_API_KEY` | the LLM role review (without it: deterministic heuristic backend) |
| `FINVIZ_API_KEY` | FinViz Elite CSV export (without it: public HTML, page-limited) |
| `TELEGRAM_BOT_TOKEN` | Telegram notifications and the command bot (without it: no Telegram) |
| `TELEGRAM_CHAT_ID` | the one chat allowed to receive pushes and issue commands (a group id is negative; every group member is then authorized) |

Prices come from yfinance — free, no key.

---

## Resources

- `references/screener_variants.md` — filter-code tables per variant, ETF data
  gaps, OTC exclusion, tuning notes
- `references/role_review_protocol.md` — the five roles, JSON schemas, score
  polarity, the Judge gate, cost model
- `scripts/state_snapshot.py` — export/import the whole database as JSON, so a
  scheduled run on a fresh checkout keeps dedupe state and PnL history, and the
  move to another host carries every open call across
- `references/telegram_bot.md` — push behaviour, command list, authorization,
  message limits and the polling model
- `references/tracker_schema.md` — SQLite schema, PnL and outcome definitions,
  every statistic and how to read it
- `assets/tracker_config.yaml` — packaged default configuration
- `scripts/fixtures/dry_run_hits.json` — three synthetic hits (one ETF) for dry
  runs and tests
- `deploy/` — systemd units, setup and update scripts, `VPS_SETUP.md`
- `agents/lowcap-{researcher,technician,skeptic,risk-manager,judge}.md` (repository
  root) — the role prompts, loaded both as Claude Code subagents and as the system
  prompts sent to the API. They live outside the skill directory because they are
  repository-level agents, so a standalone copy of this skill needs either
  `--agents-dir <path>` or those five files copied into `references/roles/`.
