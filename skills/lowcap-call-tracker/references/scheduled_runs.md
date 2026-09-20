# Scheduled runs without a server

The designed home for this tracker is a small always-on box: `deploy/setup_vps.sh`
installs a systemd timer that fires every 4 hours, keeps the SQLite database on
disk, and runs the Telegram command bot as a resident service. Nothing below is
better than that — it is what to do *before* that box exists.

## The problem a scheduled cloud session has

A scheduled Claude Code session starts from a **fresh clone**. `state/` is
gitignored, so its database is empty, which without help means:

- every run re-opens the same tickers (no dedupe),
- PnL restarts at 0% each time,
- hit rate and the TAKE-vs-shadow comparison never accumulate.

`--snapshot tracker-output/state_snapshot.json` closes that gap: the run imports
the snapshot into its empty database before screening and rewrites it afterwards,
and the session commits the file back to the branch. The next firing clones a
repo that already contains the state. See `scripts/state_snapshot.py`.

## Shape of the scheduled run

```bash
git checkout <branch> && git pull --ff-only
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-<your chat id>}"
uv run --extra ci python skills/lowcap-call-tracker/scripts/run_cycle.py \
  --backend heuristic --screen-mode public \
  --snapshot tracker-output/state_snapshot.json
git add tracker-output/ && git commit -m "chore(lowcap-tracker): scheduled run <id>" \
  && git push origin <branch>
```

No `--force-screen`: on weekends and US holidays the cycle is supposed to skip
screening and only refresh prices.

## Credentials

`TELEGRAM_BOT_TOKEN` must reach the fired session **as an environment variable of
the environment**, set in the Claude Code environment settings. Do not put it in
the routine's prompt: a stored prompt is a stored secret, and the tooling refuses
it. Without the variable the cycle still screens, reviews, tracks and commits —
only the push is skipped, and the run reports
`telegram: not sent (TELEGRAM_BOT_TOKEN is not set)`.

`ANTHROPIC_API_KEY` is optional in the same way: absent, the five roles run on the
deterministic heuristic backend, which is what `--backend heuristic` asks for
anyway.

## What this setup cannot do

- **Answer commands.** `/stats` and `/open` need the long-polling bot running
  continuously (`telegram_bot.py --poll`). A session that exists for two minutes
  every four hours cannot hold a poll open. Push notifications work; replies do
  not. That is the single biggest reason to move to a real host.
- **Survive an unavailable scheduler.** A paused subscription or a disabled
  routine stops the runs; a systemd timer on a VPS does not.
- **Keep sub-4-hour state.** Anything not in the snapshot dies with the session.

## Moving to the VPS later

The snapshot is the migration path — history comes along:

```bash
python3 skills/lowcap-call-tracker/scripts/state_snapshot.py \
  --import tracker-output/state_snapshot.json
```

Then disable the routine, and let the systemd timer own the schedule.
