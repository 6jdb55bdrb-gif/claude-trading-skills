#!/usr/bin/env bash
# Update command: pull the latest code, refresh dependencies, restart the timers.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lowcap-tracker}"
REPO_DIR="${REPO_DIR:-$APP_DIR/repo}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"

echo "==> pulling latest code"
cd "$REPO_DIR"
git pull --ff-only

echo "==> refreshing dependencies"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r skills/lowcap-call-tracker/requirements.txt

echo "==> reinstalling unit files"
install -m 644 skills/lowcap-call-tracker/deploy/lowcap-tracker.service /etc/systemd/system/
install -m 644 skills/lowcap-call-tracker/deploy/lowcap-tracker.timer /etc/systemd/system/
install -m 644 skills/lowcap-call-tracker/deploy/lowcap-learning.service /etc/systemd/system/
install -m 644 skills/lowcap-call-tracker/deploy/lowcap-learning.timer /etc/systemd/system/
install -m 644 skills/lowcap-call-tracker/deploy/lowcap-telegram.service /etc/systemd/system/
systemctl daemon-reload
systemctl restart lowcap-tracker.timer lowcap-learning.timer
# Only bounce the bot when it is enabled; an unconfigured bot stays off.
if systemctl is-enabled --quiet lowcap-telegram.service 2>/dev/null; then
    systemctl restart lowcap-telegram.service
fi

echo "==> done. Timers:"
systemctl list-timers 'lowcap-*' --no-pager
