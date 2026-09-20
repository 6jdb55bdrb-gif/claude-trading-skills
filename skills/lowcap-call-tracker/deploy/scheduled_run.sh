#!/usr/bin/env bash
# One scheduled tracker cycle for a throwaway checkout (a scheduled cloud
# session, CI, a container). Everything a scheduler needs is in here, so the
# schedule's prompt is one line and nothing depends on an agent's judgement.
#
# It pulls, runs the cycle against the committed JSON state snapshot, commits
# the refreshed state back, and prints a machine-readable summary. On a server
# with a real disk use the systemd timer instead (deploy/lowcap-tracker.timer).
#
# Credentials come from the environment and are never printed:
#   TELEGRAM_BOT_TOKEN  absent -> the cycle still runs, Telegram is skipped
#   TELEGRAM_CHAT_ID    defaults to the value baked in below
#
# Usage:
#   bash skills/lowcap-call-tracker/deploy/scheduled_run.sh [--no-push] [--notify always]
set -uo pipefail

BRANCH="${TRACKER_BRANCH:-claude/lowcap-screener-role-review-8vfirh}"
SNAPSHOT="tracker-output/state_snapshot.json"
NOTIFY=""
PUSH=1

while [ $# -gt 0 ]; do
    case "$1" in
        --no-push) PUSH=0; shift ;;
        --notify) NOTIFY="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

say() { echo "[scheduled_run] $*"; }

# ---------------------------------------------------------------- 1. refresh
if [ -d .git ]; then
    git checkout -q "$BRANCH" 2>/dev/null || say "WARNING: branch $BRANCH not checked out"
    git pull -q --ff-only 2>/dev/null || say "WARNING: git pull failed; running on the local checkout"
fi

# ------------------------------------------------------------ 2. interpreter
# Only what this skill imports — not the repository's full CI extra, which
# drags in scipy/statsmodels and turns a cold container into a slow one.
RUNNER=(uv run --no-project --with requests --with beautifulsoup4 --with pyyaml --with yfinance python)
if ! command -v uv >/dev/null 2>&1; then
    RUNNER=(python3)
    say "uv not found; falling back to system python3"
fi

export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-7565532974}"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    say "telegram credentials: present"
else
    say "telegram credentials: MISSING (cycle runs, notification skipped)"
fi

# ----------------------------------------------------------------- 3. cycle
ARGS=(skills/lowcap-call-tracker/scripts/run_cycle.py
      --backend heuristic --screen-mode public --snapshot "$SNAPSHOT")
[ -n "$NOTIFY" ] && ARGS+=(--notify "$NOTIFY")

say "running cycle"
OUTPUT="$("${RUNNER[@]}" "${ARGS[@]}" 2>&1)"
STATUS=$?
echo "$OUTPUT" | grep -vE "HTTP Error|possibly delisted|^\[|^1 Failed|^\\\$" | tail -40

if [ $STATUS -ne 0 ]; then
    say "RESULT: cycle failed (exit $STATUS)"
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
        ERR="$(echo "$OUTPUT" | tail -5)" "${RUNNER[@]}" - <<'PY' || true
import os, sys
sys.path.insert(0, "skills/lowcap-call-tracker/scripts")
from config import load_config
import telegram_bot as tb
tb.notify(load_config(), "⚠️ <b>Scheduled run failed</b>\n<pre>"
          + tb.escape_html(os.environ.get("ERR", "")[:800]) + "</pre>")
PY
    fi
    exit $STATUS
fi

RUN_ID="$(echo "$OUTPUT" | grep -oE 'run_[0-9]{8}T[0-9]{6}Z' | head -1)"
SENT="$(echo "$OUTPUT" | grep -oE 'telegram: (sent|not sent.*)' | head -1)"

# ------------------------------------------------------------ 4. persist state
COMMITTED="no"
if [ "$PUSH" = "1" ] && [ -d .git ]; then
    git add tracker-output/ 2>/dev/null
    if git diff --cached --quiet -- tracker-output/; then
        say "tracker-output unchanged; nothing to commit"
    else
        git -c user.name="lowcap-tracker" -c user.email="lowcap-tracker@localhost" \
            commit -q -m "chore(lowcap-tracker): scheduled run ${RUN_ID:-unknown}" \
            && COMMITTED="committed"
        if git push -q origin "$BRANCH" 2>/dev/null; then
            COMMITTED="pushed"
        else
            say "WARNING: git push failed; state is committed locally only"
        fi
    fi
fi

say "RESULT: ok run=${RUN_ID:-unknown} ${SENT:-telegram: unknown} state=$COMMITTED"
