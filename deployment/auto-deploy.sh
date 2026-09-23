#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/threads.avicennarabama.com/threads-product-radar}"
APP_USER="${APP_USER:?APP_USER must be set}"
BRANCH="${BRANCH:-main}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
SERVICE_NAME="${SERVICE_NAME:-threads-product-radar.service}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Auto-deploy must be run by root through systemd." >&2
  exit 1
fi

exec 9>/var/lock/threads-product-radar-deploy.lock
flock -n 9 || exit 0

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "$APP_DIR is not a Git checkout." >&2
  exit 1
fi

if [[ -n "$(sudo -u "$APP_USER" -H git -C "$APP_DIR" status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked files contain local changes; automatic deployment stopped." >&2
  exit 1
fi

sudo -u "$APP_USER" -H git -C "$APP_DIR" fetch --quiet origin "$BRANCH"

CURRENT_SHA="$(sudo -u "$APP_USER" -H git -C "$APP_DIR" rev-parse HEAD)"
TARGET_SHA="$(sudo -u "$APP_USER" -H git -C "$APP_DIR" rev-parse "origin/$BRANCH")"

if [[ "$CURRENT_SHA" == "$TARGET_SHA" ]]; then
  exit 0
fi

echo "Deploying $CURRENT_SHA -> $TARGET_SHA"
sudo -u "$APP_USER" -H git -C "$APP_DIR" merge --ff-only "$TARGET_SHA"
sudo -u "$APP_USER" -H "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

systemctl restart "$SERVICE_NAME"

for attempt in $(seq 1 12); do
  if curl --fail --silent "$HEALTH_URL" >/dev/null; then
    echo "Deployment healthy at $TARGET_SHA"
    exit 0
  fi
  sleep 5
done

echo "Health check failed after deployment" >&2
systemctl status "$SERVICE_NAME" --no-pager >&2 || true
journalctl -u "$SERVICE_NAME" -n 120 --no-pager >&2 || true
exit 1
