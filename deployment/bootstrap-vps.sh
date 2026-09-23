#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-threads.avicennarabama.com}"
SITE_ROOT="${SITE_ROOT:-/home/$DOMAIN}"
PUBLIC_HTML="$SITE_ROOT/public_html"
APP_DIR="${APP_DIR:-$SITE_ROOT/threads-product-radar}"
REPOSITORY_URL="${REPOSITORY_URL:-https://github.com/Ranneciva28/threads-product-radar.git}"
BRANCH="${BRANCH:-main}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this bootstrap as root." >&2
  exit 1
fi

for command in git curl flock systemctl python3 sudo stat sed ss; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command is missing: $command" >&2
    exit 1
  fi
done

if [[ ! -d "$PUBLIC_HTML" ]]; then
  echo "CyberPanel website was not found at $PUBLIC_HTML." >&2
  echo "Create $DOMAIN in CyberPanel first, then rerun this script." >&2
  exit 1
fi

APP_USER="$(stat -c '%U' "$PUBLIC_HTML")"
APP_GROUP="$(stat -c '%G' "$PUBLIC_HTML")"

if [[ "$APP_USER" == "root" || "$APP_USER" == "UNKNOWN" ]]; then
  echo "Refusing to run the application as root. Check ownership of $PUBLIC_HTML." >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "python3-venv is required. Install it with: apt-get install -y python3-venv" >&2
  exit 1
fi

if [[ -d "$APP_DIR/.git" ]]; then
  sudo -u "$APP_USER" -H git -C "$APP_DIR" fetch origin "$BRANCH"
  sudo -u "$APP_USER" -H git -C "$APP_DIR" checkout "$BRANCH"
  sudo -u "$APP_USER" -H git -C "$APP_DIR" merge --ff-only "origin/$BRANCH"
else
  if [[ -e "$APP_DIR" ]]; then
    echo "$APP_DIR exists but is not a Git checkout. Stop and inspect it first." >&2
    exit 1
  fi

  install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR"
  sudo -u "$APP_USER" -H git clone --branch "$BRANCH" --single-branch \
    "$REPOSITORY_URL" "$APP_DIR"
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
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
  } > "$APP_DIR/.env"
  chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
else
  echo "Existing .env preserved."
fi

install -d -o "$APP_USER" -g "$APP_GROUP" "$APP_DIR/data"

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  sudo -u "$APP_USER" -H python3 -m venv "$APP_DIR/.venv"
fi

sudo -u "$APP_USER" -H "$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
sudo -u "$APP_USER" -H "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq '(^|:)8501$'; then
  if ! systemctl is-active --quiet threads-product-radar.service; then
    echo "Port 8501 is occupied by a service not managed by threads-product-radar.service." >&2
    exit 1
  fi
fi

sed \
  -e "s|@APP_USER@|$APP_USER|g" \
  -e "s|@APP_GROUP@|$APP_GROUP|g" \
  -e "s|@APP_DIR@|$APP_DIR|g" \
  "$APP_DIR/deployment/threads-product-radar.service" \
  > /etc/systemd/system/threads-product-radar.service

sed \
  -e "s|@APP_USER@|$APP_USER|g" \
  -e "s|@APP_GROUP@|$APP_GROUP|g" \
  -e "s|@APP_DIR@|$APP_DIR|g" \
  "$APP_DIR/deployment/threads-product-radar-deploy.service" \
  > /etc/systemd/system/threads-product-radar-deploy.service

install -m 0644 "$APP_DIR/deployment/threads-product-radar-deploy.timer" \
  /etc/systemd/system/threads-product-radar-deploy.timer
chmod +x "$APP_DIR/deployment/auto-deploy.sh"

systemctl daemon-reload
systemctl enable threads-product-radar.service
systemctl restart threads-product-radar.service
systemctl enable --now threads-product-radar-deploy.timer

for attempt in $(seq 1 12); do
  if curl --fail --silent "$HEALTH_URL" >/dev/null; then
    echo
    echo "Threads Product Radar is healthy without Docker."
    echo "Application user: $APP_USER"
    echo "Application path: $APP_DIR"
    echo "Internal URL: http://127.0.0.1:8501"
    echo "Auto-deploy timer is active."
    echo "Point the CyberPanel/OpenLiteSpeed vhost for $DOMAIN to 127.0.0.1:8501."
    exit 0
  fi
  sleep 5
done

echo "Application failed its health check." >&2
systemctl status threads-product-radar.service --no-pager >&2 || true
journalctl -u threads-product-radar.service -n 120 --no-pager >&2 || true
exit 1
