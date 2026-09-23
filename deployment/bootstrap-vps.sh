#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/threads-product-radar"
REPOSITORY_URL="https://github.com/Ranneciva28/threads-product-radar.git"
HEALTH_URL="http://127.0.0.1:8501/_stcore/health"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this bootstrap as root." >&2
  exit 1
fi

for command in git docker curl flock systemctl; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command is missing: $command" >&2
    exit 1
  fi
done

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is not available." >&2
  exit 1
fi

systemctl enable --now docker

if [[ -d "$APP_DIR/.git" ]]; then
  cd "$APP_DIR"
  git fetch origin main
  git checkout main
  git merge --ff-only origin/main
else
  if [[ -e "$APP_DIR" ]]; then
    echo "$APP_DIR exists but is not a Git checkout. Stop and inspect it first." >&2
    exit 1
  fi
  git clone --branch main --single-branch "$REPOSITORY_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

if [[ ! -f .env ]]; then
  read -r -p "Dashboard username [admin]: " APP_USERNAME_INPUT
  APP_USERNAME_INPUT="${APP_USERNAME_INPUT:-admin}"

  while true; do
    read -r -s -p "Dashboard password (minimum 12 characters): " APP_PASSWORD_INPUT
    echo
    if [[ ${#APP_PASSWORD_INPUT} -ge 12 ]]; then
      break
    fi
    echo "Password is too short."
  done

  read -r -s -p "Threads access token (optional for demo mode): " THREADS_TOKEN_INPUT
  echo

  umask 077
  {
    printf 'APP_ENV=production\n'
    printf 'APP_USERNAME=%s\n' "$APP_USERNAME_INPUT"
    printf 'APP_PASSWORD=%s\n' "$APP_PASSWORD_INPUT"
    printf 'THREADS_ACCESS_TOKEN=%s\n' "$THREADS_TOKEN_INPUT"
    printf 'THREADS_API_BASE_URL=https://graph.threads.net/v1.0\n'
    printf 'THREADS_SEARCH_ENDPOINT=/keyword_search\n'
    printf 'DATABASE_PATH=data/threads_product_radar.db\n'
    printf 'DEFAULT_DATE_DAYS=30\n'
    printf 'MAX_POSTS=250\n'
    printf 'LOG_LEVEL=INFO\n'
  } > .env
  chmod 600 .env
else
  echo "Existing .env preserved."
fi

if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq '(^|:)8501$'; then
  if ! curl --fail --silent "$HEALTH_URL" >/dev/null 2>&1; then
    echo "Port 8501 is already occupied by another service." >&2
    exit 1
  fi
fi

mkdir -p data
chmod +x deployment/auto-deploy.sh

docker compose build --pull
docker compose up -d --remove-orphans

install -m 0644 deployment/threads-product-radar-deploy.service \
  /etc/systemd/system/threads-product-radar-deploy.service
install -m 0644 deployment/threads-product-radar-deploy.timer \
  /etc/systemd/system/threads-product-radar-deploy.timer

systemctl daemon-reload
systemctl enable --now threads-product-radar-deploy.timer

for attempt in $(seq 1 12); do
  if curl --fail --silent "$HEALTH_URL" >/dev/null; then
    echo
    echo "Threads Product Radar is healthy."
    echo "Auto-deploy timer is active."
    echo "Application path: $APP_DIR"
    echo "Internal URL: $HEALTH_URL"
    exit 0
  fi
  sleep 5
done

echo "Application failed its health check." >&2
docker compose logs --tail=120 >&2
exit 1

