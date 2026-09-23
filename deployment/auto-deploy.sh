#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/threads-product-radar}"
BRANCH="${BRANCH:-main}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"

exec 9>/var/lock/threads-product-radar-deploy.lock
flock -n 9 || exit 0

cd "$APP_DIR"
git fetch --quiet origin "$BRANCH"

CURRENT_SHA="$(git rev-parse HEAD)"
TARGET_SHA="$(git rev-parse "origin/$BRANCH")"

if [[ "$CURRENT_SHA" == "$TARGET_SHA" ]]; then
  exit 0
fi

echo "Deploying $CURRENT_SHA -> $TARGET_SHA"
git merge --ff-only "$TARGET_SHA"
docker compose build --pull
docker compose up -d --remove-orphans

for attempt in $(seq 1 12); do
  if curl --fail --silent "$HEALTH_URL" >/dev/null; then
    echo "Deployment healthy at $TARGET_SHA"
    exit 0
  fi
  sleep 5
done

echo "Health check failed after deployment" >&2
docker compose logs --tail=120 >&2
exit 1

