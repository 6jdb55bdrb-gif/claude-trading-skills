---
layout: default
title: "Lowcap Call Tracker"
grand_parent: English
parent: Skill Guides
nav_order: 40
lang_peer: /ja/skills/lowcap-call-tracker/
permalink: /en/skills/lowcap-call-tracker/
generated: true
---

# Lowcap Call Tracker
{: .no_toc }

Screen US low-cap stocks and ETFs for explosive moves, run every hit through a five-role review (Researcher, Technician, Skeptic, Risk Manager, Judge), and track the resulting calls and shadow calls in SQLite with PnL, hit rate and per-role accuracy. Use when the user asks for low-float / short-squeeze / momentum-breakout screening, wants candidates argued over before they become calls, wants to track whether their calls were right, wants run summaries and call statistics pushed to Telegram, or wants the tracker deployed on a VPS to run every 4 hours.
{: .fs-6 .fw-300 }

<span class="badge badge-free">No API</span> <span class="badge badge-optional">FINVIZ Optional</span>

[Download Skill Package (.skill)](https://github.com/tradermonty/claude-trading-skills/raw/main/skill-packages/lowcap-call-tracker.skill){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View Source on GitHub](https://github.com/tradermonty/claude-trading-skills/tree/main/skills/lowcap-call-tracker){: .btn .fs-5 .mb-4 .mb-md-0 }

<details open markdown="block">
  <summary>Table of Contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## 1. Overview

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

---

## 2. When to Use

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

---

## 3. Prerequisites

- **FINVIZ Elite** optional (improves performance)
- FINVIZ Elite CSV export when FINVIZ_API_KEY is set; otherwise the public screener HTML is parsed (page-limited)
- Python 3.9+ recommended

---

## 4. Quick Start

```bash
python3 skills/lowcap-call-tracker/scripts/screener_variants.py --urls
```

---

## 5. Workflow

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

---

## 6. Resources

**References:**

- `skills/lowcap-call-tracker/references/role_review_protocol.md`
- `skills/lowcap-call-tracker/references/screener_variants.md`
- `skills/lowcap-call-tracker/references/telegram_bot.md`
- `skills/lowcap-call-tracker/references/tracker_schema.md`

**Scripts:**

- `skills/lowcap-call-tracker/scripts/call_db.py`
- `skills/lowcap-call-tracker/scripts/config.py`
- `skills/lowcap-call-tracker/scripts/fetch_screener.py`
- `skills/lowcap-call-tracker/scripts/heuristic_roles.py`
- `skills/lowcap-call-tracker/scripts/learning_loop.py`
- `skills/lowcap-call-tracker/scripts/llm_client.py`
- `skills/lowcap-call-tracker/scripts/market_hours.py`
- `skills/lowcap-call-tracker/scripts/price_update.py`
- `skills/lowcap-call-tracker/scripts/publish.py`
- `skills/lowcap-call-tracker/scripts/role_review.py`
- `skills/lowcap-call-tracker/scripts/run_cycle.py`
- `skills/lowcap-call-tracker/scripts/screener_variants.py`
- `skills/lowcap-call-tracker/scripts/skill_adapters.py`
- `skills/lowcap-call-tracker/scripts/stats.py`
- `skills/lowcap-call-tracker/scripts/telegram_bot.py`
