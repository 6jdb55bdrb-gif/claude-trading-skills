#!/usr/bin/env bash
# Wrapper for the Telegram command bot: long-polls until stopped.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lowcap-tracker}"
REPO_DIR="${REPO_DIR:-$APP_DIR/repo}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
LOG_FILE="${LOG_FILE:-$APP_DIR/logs/telegram.log}"
CONFIG_ARG=()
[ -f "$APP_DIR/tracker_config.yaml" ] && CONFIG_ARG=(--config "$APP_DIR/tracker_config.yaml")

mkdir -p "$(dirname "$LOG_FILE")"

# shellcheck disable=SC1091
if [ -f "$APP_DIR/.env" ]; then
    set -a
    . "$APP_DIR/.env"
    set +a
fi

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    echo "TELEGRAM_BOT_TOKEN is not set in $APP_DIR/.env; nothing to poll" >>"$LOG_FILE"
    exit 0
fi

cd "$REPO_DIR"
exec "$VENV_DIR/bin/python" skills/lowcap-call-tracker/scripts/telegram_bot.py \
    "${CONFIG_ARG[@]}" --poll >>"$LOG_FILE" 2>&1
