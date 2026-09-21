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

## Private chat or group

`TELEGRAM_CHAT_ID` accepts either:

| Target | Id shape | Notes |
|---|---|---|
| private chat with the bot | positive, e.g. `4242` | only you see the pushes |
| group / supergroup | **negative**, e.g. `-1001234567890` | everyone in the group sees them |

**A bot cannot join a group from an invite link.** The Bot API has no
join-by-invite method, so a human member adds the bot to the group
(group title → *Add members* → search the bot's `@username`). An invite link is
for people, not for bots.

**An invite link is also not a chat id.** The `+hash` in `t.me/+xxxxxxxx` is a
server-side token, not an encoded id: there is no offline conversion, and the Bot
API cannot resolve one (only MTProto user clients can). Putting a link into
`TELEGRAM_CHAT_ID` is therefore rejected up front by `normalize_chat_id`, with
the three steps to get the real id — rather than failing later with Telegram's
opaque "chat not found". Accepted forms:

| Value | Meaning |
|---|---|
| `4242` | private chat |
| `-1001234567890` | group / supergroup |
| `@lowcapcalls` | public channel or group by username |
| `https://t.me/lowcapcalls` | same, normalized to `@lowcapcalls` |
| `https://t.me/+xPW86...` | **rejected** — private invite link |

Once the bot is in the group, find the numeric id:

```bash
python3 scripts/telegram_bot.py --list-chats
```

It prints every chat with a pending update, so posting `/id@yourbot` in the group
and running the command is enough. Reading the id is non-destructive: the
getUpdates offset is untouched, so a running poller keeps working.

Two group-specific Telegram behaviours:

- **Privacy mode** (on by default) means the bot only receives commands addressed
  to it: `/stats@yourbot`. Either address commands that way, or turn privacy off
  in @BotFather (`/setprivacy` → *Disable*), or make the bot a group admin.
  `parse_command` strips the `@mention`, so both forms work.
- **Converting a basic group to a supergroup changes its id.** Re-run
  `--list-chats` and update `.env` if commands suddenly stop being authorized.

> **Authorization is per chat, not per person.** With a group id configured,
> every current and future member of that group can run `/stats`, `/open` and
> `/calls` — and `/run` if it is enabled. A group invite link can be forwarded
> by anyone who has it, so treat the link as the real access control: keep the
> group private, revoke and regenerate the link if it leaks (group → *Invite
> Links* → *Revoke*), and leave `telegram.allow_run_command` off for a shared
> group.

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
| `/report` | the whole picture in one message: open calls with PnL, anything closed, the statistics block, and when the last run happened |
| `/stats` | full statistics: hit rate, PnL, breakdowns by direction / asset type / variant / confidence, per-role accuracy |
| `/open` | open calls with live PnL |
| `/calls [n]` | the n most recent calls, default 10, capped at 50 |
| `/shadow` | open shadow calls — the ones the Judge skipped |
| `/call TICKER` | every role's verdict for one call — catalyst, trend, the Skeptic's objection, the plan, and the Judge's reasoning. This is the command for asking "why did it take that?" |
| `/last` | the most recent run: screening state, hits, new calls, closes, LLM cost |
| `/id`, `/start` | this chat's id, and whether it is authorized |
| `/help` | the command list |
| `/run` | a full tracker cycle (disabled by default) |

## Reporting rules

- **Every open call appears in every report**, including one whose price could
  not be refreshed. An unpriced call keeps its last known figures and is marked
  `⏸ no price for 3d` (the count of stale days) — a position must never
  quietly drop out of a report because a data source lost it.
- **No message ever prints `None`.** An absent number renders as `—`, and an
  empty tracker says so in words instead of "hit rate None%". A test asserts the
  string `None` appears in no message.
- Open-call lines carry the call's age in days, so a stale call is visible
  without opening the database.
- `telegram.include_role_detail` (on by default) adds each role's score and the
  Skeptic's objection under every new call, which is what makes a run summary
  judgeable rather than just a list of tickers.

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
python3 scripts/run_cycle.py --notify always    # scan now and report, even if nothing changed
python3 scripts/telegram_bot.py --report        # push the full report without scanning
python3 scripts/telegram_bot.py --setup-profile # publish the command menu + about text
python3 scripts/telegram_bot.py --list-chats    # find a chat/group id
python3 scripts/telegram_bot.py --test          # connectivity check
python3 scripts/telegram_bot.py --send-stats    # push statistics on demand
python3 scripts/telegram_bot.py --once          # answer pending commands, exit
python3 scripts/telegram_bot.py --poll          # run the command bot
python3 scripts/run_cycle.py --no-telegram      # one run without notifying
```

`--setup-profile` pushes `BOT_COMMANDS`, the description (the text Telegram shows
on an empty chat) and the short "about" text through `setMyCommands`,
`setMyDescription` and `setMyShortDescription`. It is idempotent, so re-run it
after editing the command list; `/run` is advertised only when
`telegram.allow_run_command` is on.

On a VPS the command bot is `lowcap-telegram.service` (`Restart=always`, since
long-polling drops on any network blip); `setup_vps.sh` enables it once a token
is present in `.env`. See `deploy/VPS_SETUP.md` Step 9.
