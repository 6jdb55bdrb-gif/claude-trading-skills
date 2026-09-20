# Running the tracker on a VPS — step by step

Written for someone who has never used a server. Every command is copy-paste.
Total time: about 20 minutes. Cost: about €5/month for the server plus a few
cents a day for the model calls.

What you end up with: a small Linux server that screens the market, runs the
five-role review, tracks every call, and pushes `tracker-output/stats.md` to your
GitHub repository every 4 hours — so you can read the results on your phone.

---

## What you need before you start

1. A **GitHub account** with this repository pushed to it (it can be private).
2. An **Anthropic API key** — <https://console.anthropic.com> → *API keys* →
   *Create key*. It starts with `sk-ant-`. Copy it somewhere safe now; the
   console will not show it again.
3. A **Hetzner Cloud account** (or any other provider — the steps are the same).
4. *Optional:* a **FINVIZ Elite** key. Without it the tracker reads the free
   public screener, which is slower and returns fewer rows per run.

---

## Step 1 — Create the server

1. Log in to <https://console.hetzner.cloud> and click **New project**, name it
   `trading`.
2. Click **Add server**.
3. **Location:** pick anything close to you (e.g. Nuremberg or Ashburn).
4. **Image:** `Ubuntu 24.04`.
5. **Type:** *Shared vCPU* → **CX22** (2 vCPU, 4 GB RAM, ~€4.60/month). This is
   more than enough.
6. **SSH keys:** if you already have one, add it. If this is all new, skip it —
   Hetzner will email you a root password instead.
7. **Name:** `lowcap-tracker`.
8. Click **Create & Buy now**.

After about 20 seconds you get an **IPv4 address** like `203.0.113.45`. Write it
down; `SERVER_IP` below means that number.

---

## Step 2 — Connect to the server (SSH)

**macOS / Linux:** open Terminal and run:

```bash
ssh root@SERVER_IP
```

**Windows:** open *Windows Terminal* or *PowerShell* and run the same command.

The first time it asks `Are you sure you want to continue connecting?` — type
`yes` and press Enter. Then paste the root password (right-click to paste; the
cursor will not move while you type a password — that is normal).

You are on the server when the prompt looks like `root@lowcap-tracker:~#`.

---

## Step 3 — Download the repository and run the setup script

Replace `<you>/<repo>` with your GitHub user and repository name, then paste the
whole block:

```bash
apt-get update -qq && apt-get install -y git
git clone https://github.com/<you>/<repo>.git /tmp/setup-clone
cd /tmp/setup-clone
chmod +x skills/lowcap-call-tracker/deploy/setup_vps.sh
./skills/lowcap-call-tracker/deploy/setup_vps.sh --repo https://github.com/<you>/<repo>.git
```

> Private repository? Use a
> [personal access token](https://github.com/settings/tokens) in the URL:
> `https://<token>@github.com/<you>/<repo>.git`.

The script prints eight numbered steps. It installs Python, creates the service
user, clones the repository into `/opt/lowcap-tracker/repo`, builds a virtual
environment, installs the timers, and sets up log rotation. At the end it prints
an **SSH public key**.

---

## Step 4 — Add your API key

```bash
nano /opt/lowcap-tracker/.env
```

Change the first line to your real key:

```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`.

The key lives **only** in this file, which is readable by the service user alone
and is never committed to git.

---

## Step 5 — Let the server push results back to GitHub

The setup script printed a public key that looks like
`ssh-ed25519 AAAAC3... lowcap-tracker@lowcap-tracker`.

1. Open your repository on GitHub → **Settings** → **Deploy keys** →
   **Add deploy key**.
2. Title: `lowcap-tracker VPS`. Key: paste the whole printed line.
3. **Tick "Allow write access"** — without it the server cannot push.
4. Click **Add key**.

Back on the server, point the checkout at SSH (replace `<you>/<repo>`):

```bash
sudo -u lowcap git -C /opt/lowcap-tracker/repo remote set-url origin git@github.com:<you>/<repo>.git
```

Don't want the server to push at all? Set `GIT_PUSH=0` in
`/opt/lowcap-tracker/.env` and read the statistics on the server instead
(Step 7).

---

## Step 6 — Run it once, right now

```bash
systemctl start lowcap-tracker.service
tail -f /opt/lowcap-tracker/logs/tracker.log
```

You will see the run header, any new calls with the Judge's decision, the price
update for open calls, anything closed, and the statistics table. Press `Ctrl+C`
to stop following the log (that stops the *watching*, not the tracker).

On a weekend or a market holiday the log says `screening skipped, price update
only` — that is the intended behaviour.

> Want the results pushed to your phone instead of read from a log? That is
> Step 9 — it takes about three minutes.

---

## Step 7 — Check that it keeps running

```bash
# When does it run next? (every 4 hours)
systemctl list-timers 'lowcap-*'

# Did the last run succeed?
systemctl status lowcap-tracker.service

# The last 50 log lines
tail -n 50 /opt/lowcap-tracker/logs/tracker.log

# The current statistics
cat /opt/lowcap-tracker/repo/tracker-output/stats.md
```

`Persistent=true` in the timer means a run missed while the server was off
happens as soon as it comes back, and the timer is enabled, so it survives
reboots. Want to be sure? `reboot`, wait a minute, reconnect, and run
`systemctl list-timers 'lowcap-*'` again.

On your phone: open the repository on GitHub and look at
`tracker-output/stats.md` — refreshed after every run that changes it — and
`tracker-output/improvements.md`, refreshed weekly.

---

## Step 8 — Updating later

When you change the code on your laptop and push it:

```bash
/opt/lowcap-tracker/repo/skills/lowcap-call-tracker/deploy/update.sh
```

That pulls the new code, refreshes dependencies, reinstalls the unit files and
restarts the timers.

---

## Costs and the spend cap

The four analyst roles run on the cheap model and the Judge on the stronger one,
so a run with a handful of new candidates costs single-digit cents. The exact
cost of every run is printed in the log and stored in the database.

`llm.monthly_spend_cap_usd` in the configuration (default **$10**) is a hard
ceiling: when month-to-date spend reaches it, the tracker stops calling the API
and keeps running on the built-in deterministic scoring instead. To change it,
create `/opt/lowcap-tracker/tracker_config.yaml` with just the part you want to
override:

```yaml
llm:
  monthly_spend_cap_usd: 25.0
```

The wrapper picks that file up automatically (it is merged over the defaults, so
you only state what changes).

---

## Step 9 — Telegram alerts (optional, recommended)

Get every run pushed to your phone, and ask the tracker questions from Telegram.

**1. Create the bot.** In Telegram, message [@BotFather](https://t.me/BotFather):
send `/newbot`, pick a name and a username ending in `bot`. BotFather replies
with a token that looks like `8123456789:AA...`. Copy it.

**2. Put the token on the server.**

```bash
nano /opt/lowcap-tracker/.env
```

Fill in the Telegram lines:

```
TELEGRAM_BOT_TOKEN=paste-the-token-from-botfather
TELEGRAM_CHAT_ID=
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

**3. Find your chat id.** Open your new bot in Telegram and send it `/start`,
then on the server run:

```bash
sudo -u lowcap /opt/lowcap-tracker/venv/bin/python \
  /opt/lowcap-tracker/repo/skills/lowcap-call-tracker/scripts/telegram_bot.py --once
```

The bot replies in Telegram with `Chat id: 123456789`. Put that number into
`TELEGRAM_CHAT_ID=` in `.env` (same `nano` command as above) and save.

**4. Test it.**

```bash
sudo -u lowcap /opt/lowcap-tracker/venv/bin/python \
  /opt/lowcap-tracker/repo/skills/lowcap-call-tracker/scripts/telegram_bot.py --test
```

You should get a "Lowcap tracker is wired up" message listing the commands.

**5. Turn on the command bot** (so it answers you, not just pushes):

```bash
sudo systemctl enable --now lowcap-telegram.service
systemctl status lowcap-telegram.service
```

Re-running `setup_vps.sh` does this for you once the token is in `.env`.

### Sending to a group instead of a private chat

Want the calls in a group (yourself plus others, or just a place to keep them)?

1. **Add the bot to the group** — open the group, tap its title, *Add members*,
   search your bot's `@username`, add it. A bot cannot join from an invite link;
   somebody has to add it.
2. **Post `/id@yourbot` in the group.**
3. **Read the id on the server:**

   ```bash
   sudo -u lowcap /opt/lowcap-tracker/venv/bin/python \
     /opt/lowcap-tracker/repo/skills/lowcap-call-tracker/scripts/telegram_bot.py --list-chats
   ```

   Group ids are negative, e.g. `-1001234567890`. Put that into
   `TELEGRAM_CHAT_ID=` in `/opt/lowcap-tracker/.env`.
4. **Let it hear plain commands** (optional): in @BotFather send `/setprivacy`,
   pick your bot, choose *Disable*. Without this, address the bot explicitly:
   `/stats@yourbot`. Making the bot a group admin works too.
5. Restart the bot: `sudo systemctl restart lowcap-telegram.service`.

⚠️ **Everyone in that group can command the bot** — authorization is per chat,
not per person — and anyone holding the group's invite link can join. Keep the
group private, revoke the link if it leaks (group → *Invite Links* → *Revoke*),
and leave `/run` disabled in a shared group.

### What you can send it

| Command | Reply |
|---|---|
| `/stats` | full statistics — hit rate, PnL, breakdowns, per-role accuracy |
| `/open` | open calls with live PnL |
| `/calls 20` | the most recent calls (default 10) |
| `/shadow` | the open calls the Judge skipped, tracked the same way |
| `/last` | what the most recent run did |
| `/id` | this chat's id (setup helper) |
| `/help` | the command list |

Only your chat id can use these; any other chat gets "Not authorized."
`/run` (a full cycle on demand) stays off until you set
`telegram.allow_run_command: true` — a cycle spends LLM budget.

### Quieter or louder

In `/opt/lowcap-tracker/tracker_config.yaml` (create it if it does not exist —
only the keys you list are overridden):

```yaml
telegram:
  notify_when: always        # default "changes": quiet runs stay silent
  include_role_detail: true  # add each role's score to new calls
  enabled: false             # turn Telegram off entirely
```

Then `sudo systemctl restart lowcap-telegram.service`.

---

## Troubleshooting

| Symptom | What to do |
|---|---|
| `Permission denied (publickey)` when connecting | Use the root password Hetzner emailed you, or add your SSH key in the Hetzner console and recreate the server. |
| Log says `ANTHROPIC_API_KEY is not set` | Step 4 — the key is missing or misspelled in `/opt/lowcap-tracker/.env`. The tracker still runs on the heuristic backend. |
| Log says `monthly LLM spend cap reached` | Expected once you hit the cap. Raise `llm.monthly_spend_cap_usd` or wait for the next month. |
| `git push failed` in the log | Step 5 — the deploy key is missing, lacks write access, or the remote is still HTTPS. |
| No new calls for days | Normal: these filters are tight. Check the log says `screening` ran, and try loosening a filter in the config. |
| `public screener parsing needs beautifulsoup4` | Run `update.sh` (it installs the requirements), or add a `FINVIZ_API_KEY` to use the Elite export path. |
| No Telegram messages arrive | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`, then run `telegram_bot.py --test`. The run log prints `telegram: not sent (reason)` when it is skipped. |
| Telegram says "Not authorized." | `TELEGRAM_CHAT_ID` does not match the chat you are messaging from. Send `/id` and paste the number it replies with into `.env`. |
| Bot answers pushes but not commands | The command bot is a separate service: `sudo systemctl enable --now lowcap-telegram.service`. |
| In a group the bot ignores `/stats` | Telegram privacy mode. Send `/stats@yourbot`, or disable privacy in @BotFather (`/setprivacy`), or make the bot an admin. |
| Group commands stopped working | Converting a group to a supergroup changes its id. Re-run `--list-chats` and update `TELEGRAM_CHAT_ID`. |
| `--list-chats` prints nothing | The running bot already consumed the updates. Post a new message, or `sudo systemctl stop lowcap-telegram.service` first. |
| Want to stop everything | `systemctl disable --now lowcap-tracker.timer lowcap-learning.timer lowcap-telegram.service` |
| Want to start over | `rm -rf /opt/lowcap-tracker` and re-run Step 3. |

## Where things live on the server

| Path | What it is |
|---|---|
| `/opt/lowcap-tracker/repo` | the git checkout the timer runs from |
| `/opt/lowcap-tracker/venv` | Python virtual environment |
| `/opt/lowcap-tracker/.env` | your API keys (never committed) |
| `/opt/lowcap-tracker/logs/tracker.log` | run log, rotated weekly, 8 kept |
| `/opt/lowcap-tracker/logs/telegram.log` | Telegram bot log, rotated with the rest |
| `/opt/lowcap-tracker/repo/state/lowcap_calls.db` | the SQLite call database |
| `/opt/lowcap-tracker/repo/tracker-output/stats.md` | statistics, pushed to GitHub |
| `/opt/lowcap-tracker/repo/tracker-output/improvements.md` | weekly proposals, pushed to GitHub |
