#!/usr/bin/env bash
# Wrapper invoked by the systemd timer: one tracker cycle, logged.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/lowcap-tracker}"
REPO_DIR="${REPO_DIR:-$APP_DIR/repo}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
LOG_FILE="${LOG_FILE:-$APP_DIR/logs/tracker.log}"
CONFIG_ARG=()
[ -f "$APP_DIR/tracker_config.yaml" ] && CONFIG_ARG=(--config "$APP_DIR/tracker_config.yaml")

mkdir -p "$(dirname "$LOG_FILE")"

# shellcheck disable=SC1091
if [ -f "$APP_DIR/.env" ]; then
    set -a
    . "$APP_DIR/.env"
    set +a
fi

PUSH_ARG=()
if [ "${GIT_PUSH:-0}" = "1" ]; then
    PUSH_ARG=(--git-push)
fi

cd "$REPO_DIR"
{
    echo "=============================================================="
    echo "run start: $(date -Is)"
    "$VENV_DIR/bin/python" skills/lowcap-call-tracker/scripts/run_cycle.py \
        "${CONFIG_ARG[@]}" \
        --backend "${ROLE_BACKEND:-auto}" \
        "${PUSH_ARG[@]}"
    echo "run end:   $(date -Is)"
} >>"$LOG_FILE" 2>&1
