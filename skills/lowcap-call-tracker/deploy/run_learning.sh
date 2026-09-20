#!/usr/bin/env bash
# Wrapper invoked by the weekly timer: refresh improvements.md (proposals only).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lowcap-tracker}"
REPO_DIR="${REPO_DIR:-$APP_DIR/repo}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
LOG_FILE="${LOG_FILE:-$APP_DIR/logs/learning.log}"
CONFIG_ARG=()
[ -f "$APP_DIR/tracker_config.yaml" ] && CONFIG_ARG=(--config "$APP_DIR/tracker_config.yaml")

mkdir -p "$(dirname "$LOG_FILE")"

# shellcheck disable=SC1091
if [ -f "$APP_DIR/.env" ]; then
    set -a
    . "$APP_DIR/.env"
    set +a
fi

cd "$REPO_DIR"
{
    echo "learning loop: $(date -Is)"
    "$VENV_DIR/bin/python" skills/lowcap-call-tracker/scripts/learning_loop.py \
        "${CONFIG_ARG[@]}" --write
} >>"$LOG_FILE" 2>&1
