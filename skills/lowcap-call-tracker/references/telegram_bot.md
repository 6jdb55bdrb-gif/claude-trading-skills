# Telegram bot

Two independent halves, both off unless `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` are in the environment:

| Half | Runs as | What it does |
|---|---|---|
| **Push** | part of `run_cycle.py` | a summary after every run and after the weekly learning loop |
| **Commands** | `telegram_bot.py --poll` (a systemd service) | answers `/stats`, `/open`, `/calls`, `/shadow`, `/last` |

Nothing here is required. With no token the tracker behaves exactly as before,
and the run output simply prints `telegram: not sent (TELEGRAM_BOT_TOKEN is not
set)`.

## Credentials and authorization

- The token is read **only** from the environment, never from
  `tracker_config.yaml` — a leaked config file cannot control the bot, and the
  config is safe to commit.
- `TELEGRAM_CHAT_ID` is the one chat allowed to command the bot;
  `telegram.extra_chat_ids` adds more (a second device, a partner).
- Any other chat gets `Not authorized.` and no data. `/id` and `/start` are the
  only commands answered everywhere, because discovering the chat id is a setup
  step — and they return nothing but that chat's own id.
- `/run` executes a full cycle, so it is disabled unless
  `telegram.allow_run_command: true`.

## Push behaviour

| Key | Default | Effect |
|---|---|---|
| `telegram.enabled` | `true` | master switch (still needs a token) |
| `telegram.notify_when` | `changes` | `changes` = only runs with a new call, a close or an error; `always` = every run, including quiet weekend price-only runs |
| `telegram.include_stats` | `true` | append the compact statistics block |
| `telegram.include_role_detail` | `false` | add each role's score and the Skeptic's objection under every new call |
| `telegram.silent_when_quiet` | `true` | a run with nothing opened or closed arrives without a notification sound |

A run notification carries, in order: the session line (so a skipped weekend
screen is obvious), new calls with the Judge's decision and one-line reason,
open calls with live PnL, anything closed at the threshold, the statistics
block, the LLM cost with month-to-date spend against the cap, and any errors.

**A failing bot never fails a run.** `notify_run` catches its own errors and
records them in the run report (`telegram: not sent (…)`); the cycle's database
writes, statistics and git push all happen regardless.

## Commands

| Command | Reply |
|---|---|
| `/stats` | full statistics: hit rate, PnL, breakdowns by direction / asset type / variant / confidence, per-role accuracy |
| `/open` | open calls with live PnL |
| `/calls [n]` | the n most recent calls, default 10, capped at 50 |
| `/shadow` | open shadow calls — the ones the Judge skipped |
| `/last` | the most recent run: screening state, hits, new calls, closes, LLM cost |
| `/id`, `/start` | this chat's id, and whether it is authorized |
| `/help` | the command list |
| `/run` | a full tracker cycle (disabled by default) |

## Message mechanics

- Messages use HTML parse mode; every interpolated value goes through
  `escape_html`, so a company name containing `&` or `<` cannot break the
  message or inject markup.
- Telegram rejects anything over 4096 characters. `split_message` splits on line
  boundaries at `telegram.max_message_chars` (default 3900) and hard-splits a
  single overlong line, so a 60-call `/stats` reply arrives as several messages
  rather than an API error.
- `sendMessage` retries a `429` using Telegram's own `retry_after`, and retries
  transport errors with backoff, three attempts in total.

## Polling

`telegram_bot.py --poll` long-polls `getUpdates` (`telegram.poll_timeout_seconds`,
default 50). The next offset is persisted to `telegram.offset_file`
(`state/lowcap_telegram_offset.json`), so a restart never replays commands that
were already answered. A command that raises replies with the error instead of
killing the loop.

`--once` drains whatever is pending and exits — that is the setup path (`/start`
in Telegram, then `--once` on the server tells you your chat id) and the shape
the tests drive.

## Operating

```bash
python3 scripts/telegram_bot.py --test          # connectivity check
python3 scripts/telegram_bot.py --send-stats    # push statistics on demand
python3 scripts/telegram_bot.py --once          # answer pending commands, exit
python3 scripts/telegram_bot.py --poll          # run the command bot
python3 scripts/run_cycle.py --no-telegram      # one run without notifying
```

On a VPS the command bot is `lowcap-telegram.service` (`Restart=always`, since
long-polling drops on any network blip); `setup_vps.sh` enables it once a token
is present in `.env`. See `deploy/VPS_SETUP.md` Step 9.
