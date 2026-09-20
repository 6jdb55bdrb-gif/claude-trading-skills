#!/usr/bin/env bash
# One-shot setup for a fresh Ubuntu 24.04 VPS (e.g. Hetzner CX22).
#
# Installs Python + git, creates a service user, clones the repo, builds a venv,
# installs the tracker's dependencies, installs the systemd timer (every 4 hours,
# survives reboots) and the weekly learning timer, and wires up log rotation.
#
# Idempotent: re-running updates the checkout and the unit files in place.
#
# Usage (as root):
#   ./setup_vps.sh --repo https://github.com/<you>/<repo>.git [--branch main]
#
# Options:
#   --repo URL       git remote to clone (required on first run)
#   --branch NAME    branch to check out (default: the remote's default branch)
#   --app-dir PATH   install location (default: /opt/lowcap-tracker)
#   --user NAME      service user (default: lowcap)
#   --no-ssh-key     do not generate a deploy key
set -euo pipefail

REPO_URL=""
BRANCH=""
APP_DIR="/opt/lowcap-tracker"
SERVICE_USER="lowcap"
MAKE_SSH_KEY=1

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO_URL="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        --app-dir) APP_DIR="$2"; shift 2 ;;
        --user) SERVICE_USER="$2"; shift 2 ;;
        --no-ssh-key) MAKE_SSH_KEY=0; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run this script as root (sudo ./setup_vps.sh ...)" >&2
    exit 1
fi

REPO_DIR="$APP_DIR/repo"
VENV_DIR="$APP_DIR/venv"

if [ -z "$REPO_URL" ] && [ ! -d "$REPO_DIR/.git" ]; then
    echo "ERROR: --repo is required on the first run" >&2
    exit 1
fi

echo "==> 1/8 installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git logrotate ca-certificates tzdata

echo "==> 2/8 creating service user '$SERVICE_USER'"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
mkdir -p "$APP_DIR/logs"
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

echo "==> 3/8 cloning or updating the repository"
if [ -d "$REPO_DIR/.git" ]; then
    sudo -u "$SERVICE_USER" git -C "$REPO_DIR" fetch --all --quiet
    if [ -n "$BRANCH" ]; then
        sudo -u "$SERVICE_USER" git -C "$REPO_DIR" checkout "$BRANCH"
    fi
    sudo -u "$SERVICE_USER" git -C "$REPO_DIR" pull --ff-only
else
    if [ -n "$BRANCH" ]; then
        sudo -u "$SERVICE_USER" git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    else
        sudo -u "$SERVICE_USER" git clone "$REPO_URL" "$REPO_DIR"
    fi
fi
sudo -u "$SERVICE_USER" git -C "$REPO_DIR" config user.name "lowcap-tracker"
sudo -u "$SERVICE_USER" git -C "$REPO_DIR" config user.email "lowcap-tracker@localhost"

echo "==> 4/8 creating the virtual environment"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    sudo -u "$SERVICE_USER" python3 -m venv "$VENV_DIR"
fi
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --quiet --upgrade pip
sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --quiet \
    -r "$REPO_DIR/skills/lowcap-call-tracker/requirements.txt"

echo "==> 5/8 preparing the environment file"
if [ ! -f "$APP_DIR/.env" ]; then
    install -o "$SERVICE_USER" -g "$SERVICE_USER" -m 600 \
        "$REPO_DIR/skills/lowcap-call-tracker/deploy/.env.example" "$APP_DIR/.env"
    echo "    created $APP_DIR/.env — EDIT IT and add your ANTHROPIC_API_KEY"
else
    echo "    $APP_DIR/.env already exists, left untouched"
fi
chmod 600 "$APP_DIR/.env"

echo "==> 6/8 installing systemd units"
chmod +x "$REPO_DIR/skills/lowcap-call-tracker/deploy/"*.sh
for unit in lowcap-tracker.service lowcap-tracker.timer \
            lowcap-learning.service lowcap-learning.timer; do
    sed -e "s#/opt/lowcap-tracker#$APP_DIR#g" -e "s#^User=lowcap#User=$SERVICE_USER#" \
        -e "s#^Group=lowcap#Group=$SERVICE_USER#" \
        "$REPO_DIR/skills/lowcap-call-tracker/deploy/$unit" >"/etc/systemd/system/$unit"
    chmod 644 "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable --now lowcap-tracker.timer lowcap-learning.timer

echo "==> 7/8 installing log rotation"
sed -e "s#/opt/lowcap-tracker#$APP_DIR#g" -e "s#su lowcap lowcap#su $SERVICE_USER $SERVICE_USER#" \
    "$REPO_DIR/skills/lowcap-call-tracker/deploy/logrotate-lowcap-tracker" \
    >/etc/logrotate.d/lowcap-tracker
chmod 644 /etc/logrotate.d/lowcap-tracker

echo "==> 8/8 deploy key for pushing stats.md back to GitHub"
KEY_PATH="$APP_DIR/.ssh/id_ed25519"
if [ "$MAKE_SSH_KEY" = "1" ]; then
    if [ ! -f "$KEY_PATH" ]; then
        sudo -u "$SERVICE_USER" mkdir -p "$APP_DIR/.ssh"
        sudo -u "$SERVICE_USER" chmod 700 "$APP_DIR/.ssh"
        sudo -u "$SERVICE_USER" ssh-keygen -t ed25519 -N "" -q -f "$KEY_PATH" \
            -C "lowcap-tracker@$(hostname)"
        sudo -u "$SERVICE_USER" ssh-keyscan -t ed25519 github.com \
            >>"$APP_DIR/.ssh/known_hosts" 2>/dev/null
        chown "$SERVICE_USER:$SERVICE_USER" "$APP_DIR/.ssh/known_hosts"
    fi
    echo
    echo "    Add this public key to GitHub as a deploy key WITH WRITE ACCESS"
    echo "    (repository → Settings → Deploy keys → Add deploy key):"
    echo
    cat "$KEY_PATH.pub"
    echo
    echo "    Then switch the checkout to SSH so pushes use that key:"
    echo "      sudo -u $SERVICE_USER git -C $REPO_DIR remote set-url origin \\"
    echo "        git@github.com:<you>/<repo>.git"
    echo "    (Leave GIT_PUSH=0 in $APP_DIR/.env if you would rather not push.)"
fi

cat <<EOF

Setup complete.

  Edit the API key:      sudo nano $APP_DIR/.env
  Run one cycle now:     sudo systemctl start lowcap-tracker.service
  Watch the log:         sudo tail -f $APP_DIR/logs/tracker.log
  Next scheduled runs:   systemctl list-timers 'lowcap-*'
  Latest statistics:     cat $REPO_DIR/tracker-output/stats.md
  Update later:          sudo $REPO_DIR/skills/lowcap-call-tracker/deploy/update.sh
EOF
