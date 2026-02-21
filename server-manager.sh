#!/usr/bin/env bash
# ==============================================================================
# Jaysonkhan Server Manager (DevOps UI/UX for mobile devs) 🚀
# Project: /var/www/jaysonkhan (Django + Gunicorn + Nginx + Postgres + Redis + Tailwind)
# Usage:
#   chmod +x server-manager.sh
#   sudo ./server-manager.sh
# ==============================================================================

set -Eeuo pipefail

# --------------------------- Config (edit if needed) ---------------------------
PROJECT_DIR="/var/www/jaysonkhan"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_ACTIVATE="$BACKEND_DIR/venv/bin/activate"
PY="$BACKEND_DIR/venv/bin/python"
PIP="$BACKEND_DIR/venv/bin/pip"
MANAGE="$BACKEND_DIR/manage.py"

ENV_FILE="$PROJECT_DIR/.env"

SERVICE_APP="jaysonkhan"           # systemd service name
SOCKET_PATH="$BACKEND_DIR/jaysonkhan.sock"

NGINX_SITE="jaysonkhan"            # /etc/nginx/sites-available/<name>
NGINX_SITE_FILE="/etc/nginx/sites-available/$NGINX_SITE"

DOMAIN_MAIN="jaysonkhan.com"
DOMAIN_WWW="www.jaysonkhan.com"
PUBLIC_IP_FALLBACK="144.91.69.225"

# Tailwind scripts from package.json
CSS_BUILD_CMD="npm run css:build"
CSS_WATCH_CMD="npm run css:watch"

# Django settings module
DJANGO_SETTINGS="config.settings.prod"

# ------------------------------ UI / Colors -----------------------------------
if command -v tput >/dev/null 2>&1; then
  BOLD="$(tput bold)"; DIM="$(tput dim)"; RESET="$(tput sgr0)"
  RED="$(tput setaf 1)"; GREEN="$(tput setaf 2)"; YELLOW="$(tput setaf 3)"
  BLUE="$(tput setaf 4)"; MAGENTA="$(tput setaf 5)"; CYAN="$(tput setaf 6)"
  GRAY="$(tput setaf 7)"
else
  BOLD=""; DIM=""; RESET=""
  RED=""; GREEN=""; YELLOW=""; BLUE=""; MAGENTA=""; CYAN=""; GRAY=""
fi

ok()   { echo -e "${GREEN}${BOLD}✔${RESET} $*"; }
warn() { echo -e "${YELLOW}${BOLD}⚠${RESET} $*"; }
err()  { echo -e "${RED}${BOLD}✖${RESET} $*"; }
info() { echo -e "${CYAN}${BOLD}ℹ${RESET} $*"; }
line() { echo -e "${GRAY}────────────────────────────────────────────────────────────${RESET}"; }

pause() {
  echo
  read -r -p "$(echo -e "${DIM}Press ENTER to continue...${RESET}")" _
}

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    err "Run as root: sudo $0"
    exit 1
  fi
}

have() { command -v "$1" >/dev/null 2>&1; }

# ------------------------------ Helpers ---------------------------------------
cd_project() {
  cd "$PROJECT_DIR" 2>/dev/null || { err "Project not found: $PROJECT_DIR"; exit 1; }
}

activate_venv() {
  if [[ -f "$VENV_ACTIVATE" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_ACTIVATE"
  else
    err "Venv not found: $VENV_ACTIVATE"
    err "Expected: $BACKEND_DIR/venv/"
    exit 1
  fi
}

title() {
  clear || true
  echo -e "${MAGENTA}${BOLD}"
  cat << "EOF"
      _   _ __   ______  ___  _   _ _  ___  _   _   _   _ 
     | | / \ \ / / ___|/ _ \| \ | | |/ / | | | / \ | \ | |
  _  | |/ _ \ \ V /\___ \ | | |  \| | ' /| |_| |/ _ \|  \| |
 | |_| / ___ \ | |  ___) | |_| | |\  | . \|  _  / ___ \ |\  |
  \___/_/   \_\_| |____/ \___/|_| \_|_| \_\_| |_/_/   \_\_| \_|
EOF
  echo -e "${RESET}"
  echo -e "${BOLD}Jaysonkhan Server Manager${RESET}  ${DIM}(Django + Gunicorn + Nginx + Postgres + Redis + Tailwind)${RESET}"
  line
}

human_bytes() {
  # input: bytes
  local b="${1:-0}"
  awk -v b="$b" 'function human(x){s="BKMGTPE"; while(x>=1024&&length(s)>1){x/=1024;s=substr(s,2)} return sprintf("%.1f%s",x,substr(s,1,1))} BEGIN{print human(b)}'
}

get_public_ip() {
  local ip=""
  if have curl; then
    ip="$(curl -fsS https://api.ipify.org 2>/dev/null || true)"
  fi
  echo "${ip:-$PUBLIC_IP_FALLBACK}"
}

service_status_line() {
  local svc="$1"
  local state
  state="$(systemctl is-active "$svc" 2>/dev/null || true)"
  if [[ "$state" == "active" ]]; then
    echo -e "${GREEN}ACTIVE${RESET}"
  elif [[ "$state" == "inactive" ]]; then
    echo -e "${YELLOW}INACTIVE${RESET}"
  else
    echo -e "${RED}${state:-unknown}${RESET}"
  fi
}

port_listening() {
  local port="$1"
  if have ss; then
    ss -lntp 2>/dev/null | grep -qE ":\b${port}\b" && return 0 || return 1
  elif have netstat; then
    netstat -lntp 2>/dev/null | grep -qE ":\b${port}\b" && return 0 || return 1
  fi
  return 1
}

socket_exists() {
  [[ -S "$SOCKET_PATH" ]]
}

nginx_static_hint() {
  # quick heuristic: show if 'alias /var/www/jaysonkhan/static/;' exists
  if [[ -f "$NGINX_SITE_FILE" ]] && grep -qE 'location /static/.*alias /var/www/jaysonkhan/static/' "$NGINX_SITE_FILE"; then
    ok "Nginx static mapping looks OK (alias found)."
  else
    warn "Nginx static mapping may be wrong. Expected alias for /static/ and /media/."
    info "Open: $NGINX_SITE_FILE"
  fi
}

# ------------------------------ Dashboard -------------------------------------
dashboard() {
  title

  local os kernel arch ram_total ram_used ram_free disk_total disk_used disk_free ip
  os="$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-Linux}" || echo "Linux")"
  kernel="$(uname -r 2>/dev/null || echo "?")"
  arch="$(uname -m 2>/dev/null || echo "?")"
  ip="$(get_public_ip)"

  # RAM
  if have free; then
    # Values in MiB
    read -r _ total used free _ < <(free -m | awk '/^Mem:/ {print $1,$2,$3,$4,$5}')
    ram_total="${total} MB"
    ram_used="${used} MB"
    ram_free="${free} MB"
  else
    ram_total="?"
    ram_used="?"
    ram_free="?"
  fi

  # Disk for /
  if have df; then
    read -r _ dtotal dused davail _ < <(df -h / | awk 'NR==2 {print $1,$2,$3,$4,$5}')
    disk_total="$dtotal"
    disk_used="$dused"
    disk_free="$davail"
  else
    disk_total="?"
    disk_used="?"
    disk_free="?"
  fi

  echo -e "${BOLD}Server Umumiy Ko'rinishi${RESET}"
  echo -e "OS: ${BOLD}${os}${RESET}  | Kernel: ${kernel} (${arch})"
  echo -e "RAM: ${BOLD}${ram_total}${RESET}  (used: ${ram_used}, free: ${ram_free})"
  echo -e "Disk (/): ${BOLD}${disk_total}${RESET}  (used: ${disk_used}, free: ${disk_free})"
  echo -e "Public IP: ${BOLD}${ip}${RESET}"
  line

  echo -e "${BOLD}Ishlab turgan xizmatlar${RESET}"
  printf "%-22s %-12s %-18s\n" "Service" "State" "Notes"
  printf "%-22s %-12b %-18s\n" "nginx" "$(service_status_line nginx)" "Ports: 80/443"
  printf "%-22s %-12b %-18s\n" "postgresql" "$(service_status_line postgresql)" "Local: 5432"
  printf "%-22s %-12b %-18s\n" "redis-server" "$(service_status_line redis-server)" "Local: 6379"
  printf "%-22s %-12b %-18s\n" "$SERVICE_APP" "$(service_status_line "$SERVICE_APP")" "Gunicorn + socket"
  line

  echo -e "${BOLD}Loyiha: ${DOMAIN_MAIN}${RESET}"
  echo -e "Path: ${BOLD}${PROJECT_DIR}${RESET}"
  echo -e "Backend: ${BOLD}${BACKEND_DIR}${RESET}"
  echo -e "Venv: ${BOLD}${VENV_ACTIVATE}${RESET}"
  echo -e "Env:  ${BOLD}${ENV_FILE}${RESET}  $( [[ -f "$ENV_FILE" ]] && echo -e "${GREEN}(found)${RESET}" || echo -e "${RED}(missing)${RESET}" )"
  echo -e "Socket: ${BOLD}${SOCKET_PATH}${RESET}  $( socket_exists && echo -e "${GREEN}(exists)${RESET}" || echo -e "${RED}(missing)${RESET}" )"
  nginx_static_hint
  line
}

# ------------------------------ Actions ---------------------------------------
action_status_deep() {
  dashboard
  echo -e "${BOLD}Deep checks${RESET}"
  echo -e "Nginx test: "
  if nginx -t >/dev/null 2>&1; then ok "nginx -t OK"; else err "nginx -t FAILED"; fi

  echo -e "Ports:"
  if port_listening 80; then ok "80 listening"; else warn "80 not listening (maybe only 443?)"; fi
  if port_listening 443; then ok "443 listening"; else warn "443 not listening"; fi

  echo -e "DNS/HTTP quick:"
  if have curl; then
    curl -fsSI "https://${DOMAIN_MAIN}" >/dev/null 2>&1 && ok "HTTPS responds: ${DOMAIN_MAIN}" || warn "HTTPS not responding or blocked."
    curl -fsSI "https://${DOMAIN_MAIN}/static/" >/dev/null 2>&1 && ok "/static reachable" || warn "/static may be 404 (check alias/path)."
  else
    warn "curl not installed; skipping HTTP checks."
  fi
  pause
}

action_logs() {
  title
  echo -e "${BOLD}Logs Viewer${RESET}"
  echo -e "${DIM}1) App (gunicorn) logs  2) Nginx error  3) Nginx access  4) Postgres  5) Redis  0) Back${RESET}"
  echo
  read -r -p "Choose: " ch
  case "$ch" in
    1) journalctl -u "$SERVICE_APP" -n 200 --no-pager || true; pause ;;
    2) tail -n 200 /var/log/nginx/error.log 2>/dev/null || echo "No /var/log/nginx/error.log"; pause ;;
    3) tail -n 200 /var/log/nginx/access.log 2>/dev/null || echo "No /var/log/nginx/access.log"; pause ;;
    4) journalctl -u postgresql -n 200 --no-pager || true; pause ;;
    5) journalctl -u redis-server -n 200 --no-pager || true; pause ;;
    0) return ;;
    *) warn "Invalid choice"; pause ;;
  esac
}

action_restart_services() {
  title
  echo -e "${BOLD}Restart Services${RESET}"
  echo -e "${DIM}This will restart: $SERVICE_APP, nginx${RESET}"
  echo
  read -r -p "Continue? (y/N): " yn
  [[ "${yn,,}" == "y" ]] || { info "Cancelled."; pause; return; }

  systemctl daemon-reload
  systemctl restart "$SERVICE_APP"
  systemctl restart nginx

  ok "Restarted $SERVICE_APP and nginx."
  systemctl status "$SERVICE_APP" --no-pager -l || true
  pause
}

action_build_css() {
  title
  echo -e "${BOLD}Tailwind CSS Build${RESET}"
  echo -e "${DIM}Generates: backend/static/css/output.css${RESET}"
  echo
  cd_project

  if ! have node || ! have npm; then
    err "node/npm not found."
    info "Install Node 20: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
    pause
    return
  fi

  info "Node: $(node -v) | npm: $(npm -v)"
  echo

  # Ensure deps installed
  if [[ ! -d "$PROJECT_DIR/node_modules" ]]; then
    warn "node_modules not found. Installing dependencies..."
    npm install
  fi

  info "Running: $CSS_BUILD_CMD"
  eval "$CSS_BUILD_CMD"

  if [[ -f "$BACKEND_DIR/static/css/output.css" ]]; then
    ok "CSS generated: $BACKEND_DIR/static/css/output.css"
  else
    warn "CSS file not found yet. Check build output."
  fi

  pause
}

action_build_css_watch() {
  title
  echo -e "${BOLD}Tailwind CSS Watch (Dev)${RESET}"
  echo -e "${DIM}Press CTRL+C to stop watching.${RESET}"
  echo
  cd_project

  if ! have node || ! have npm; then
    err "node/npm not found."
    pause
    return
  fi
  npm install >/dev/null 2>&1 || true
  eval "$CSS_WATCH_CMD"
}

action_django_migrate() {
  title
  echo -e "${BOLD}Django Migrate${RESET}"
  echo
  cd "$BACKEND_DIR"
  activate_venv

  info "Running migrations (settings: $DJANGO_SETTINGS)"
  "$PY" "$MANAGE" migrate --settings="$DJANGO_SETTINGS"
  ok "Migrate done."
  pause
}

action_collectstatic() {
  title
  echo -e "${BOLD}Django collectstatic${RESET}"
  echo
  cd "$BACKEND_DIR"
  activate_venv

  info "Collecting static (settings: $DJANGO_SETTINGS)"
  "$PY" "$MANAGE" collectstatic --noinput --settings="$DJANGO_SETTINGS"
  ok "collectstatic done."
  pause
}

action_deploy_full() {
  title
  echo -e "${BOLD}Full Deploy (Git pull + deps + CSS + migrate + collectstatic + restart)${RESET}"
  echo -e "${DIM}This is the “one button deploy” for you.${RESET}"
  line
  echo -e "Project: ${BOLD}${PROJECT_DIR}${RESET}"
  echo -e "Service: ${BOLD}${SERVICE_APP}${RESET}"
  echo -e "Nginx:   ${BOLD}${NGINX_SITE_FILE}${RESET}"
  line
  read -r -p "Continue deploy? (y/N): " yn
  [[ "${yn,,}" == "y" ]] || { info "Cancelled."; pause; return; }

  cd_project
  info "1) Git pull"
  git pull origin main
  ok "Git updated."

  info "2) Python deps (requirements.txt)"
  cd "$BACKEND_DIR"
  activate_venv
  "$PIP" install -r "$PROJECT_DIR/requirements.txt"
  ok "Python deps OK."

  info "3) Node deps + CSS build"
  cd "$PROJECT_DIR"
  if have node && have npm; then
    npm install
    eval "$CSS_BUILD_CMD" || warn "CSS build failed (check output). Continuing..."
  else
    warn "node/npm not found. Skipping CSS build."
  fi

  info "4) Django migrate"
  cd "$BACKEND_DIR"
  "$PY" "$MANAGE" migrate --settings="$DJANGO_SETTINGS"
  ok "Migrate OK."

  info "5) collectstatic"
  "$PY" "$MANAGE" collectstatic --noinput --settings="$DJANGO_SETTINGS"
  ok "collectstatic OK."

  info "6) Restart services"
  systemctl daemon-reload
  systemctl restart "$SERVICE_APP"
  systemctl reload nginx
  ok "Restarted $SERVICE_APP and reloaded nginx."

  line
  ok "DEPLOY DONE ✅"
  pause
}

action_fix_permissions() {
  title
  echo -e "${BOLD}Fix Permissions (static/media → www-data, 755)${RESET}"
  echo
  read -r -p "Apply permissions now? (y/N): " yn
  [[ "${yn,,}" == "y" ]] || { info "Cancelled."; pause; return; }

  mkdir -p "$PROJECT_DIR/static" "$PROJECT_DIR/media"
  chown -R www-data:www-data "$PROJECT_DIR/static" "$PROJECT_DIR/media"
  chmod -R 755 "$PROJECT_DIR/static" "$PROJECT_DIR/media"
  ok "Permissions fixed for static/media."
  pause
}

action_nginx_edit() {
  title
  echo -e "${BOLD}Nginx Site Editor${RESET}"
  echo -e "${DIM}File: $NGINX_SITE_FILE${RESET}"
  echo
  if [[ ! -f "$NGINX_SITE_FILE" ]]; then
    err "Not found: $NGINX_SITE_FILE"
    pause
    return
  fi
  nano "$NGINX_SITE_FILE"
  echo
  info "Testing nginx config..."
  if nginx -t; then
    ok "nginx -t OK"
    systemctl reload nginx
    ok "nginx reloaded"
  else
    err "nginx -t FAILED. Not reloading."
  fi
  pause
}

action_certbot_renew() {
  title
  echo -e "${BOLD}SSL / Certbot Renew${RESET}"
  echo
  if ! have certbot; then
    err "certbot not found."
    info "Install: sudo apt install -y certbot python3-certbot-nginx"
    pause
    return
  fi

  info "Dry-run renew (safe test)"
  certbot renew --dry-run
  ok "Dry-run finished."
  pause
}

action_backup_db() {
  title
  echo -e "${BOLD}PostgreSQL Backup${RESET}"
  echo -e "${DIM}Creates a timestamped backup in /var/backups/jaysonkhan/${RESET}"
  echo
  mkdir -p /var/backups/jaysonkhan

  # Read env values (simple parsing)
  if [[ ! -f "$ENV_FILE" ]]; then
    err ".env not found: $ENV_FILE"
    pause
    return
  fi

  local db user host port ts out pass
  # Helper to clean .env values (strip \r, quotes, and trailing spaces)
  clean_env() {
    grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" | tr -d '\r'
  }

  db="$(clean_env POSTGRES_DB)"
  user="$(clean_env POSTGRES_USER)"
  host="$(clean_env POSTGRES_HOST)"
  port="$(clean_env POSTGRES_PORT)"
  pass="$(clean_env POSTGRES_PASSWORD)"

  # Force IPv4 if localhost to avoid ::1 authentication issues in Postgres
  if [[ "$host" == "localhost" || -z "$host" ]]; then
    host="127.0.0.1"
  fi

  if [[ -z "$db" || -z "$user" ]]; then
    err "POSTGRES_DB/POSTGRES_USER not found in .env"
    pause
    return
  fi

  ts="$(date +%Y%m%d_%H%M%S)"
  out="/var/backups/jaysonkhan/${db}_${ts}.dump"

  info "Backup: db=${db}, user=${user}, host=${host}, port=${port:-5432}"
  info "Debug: PGPASSWORD length is ${#pass} chars."
  info "Output: $out"
  echo
  warn "Using PGPASSWORD environment variable for authentication."

  # Run pg_dump (custom format)
  PGPASSWORD="$pass" \
    pg_dump -Fc -h "$host" -p "${port:-5432}" -U "$user" "$db" -f "$out"

  ok "Backup created: $out"
  pause
}

action_healthcheck() {
  title
  echo -e "${BOLD}Healthcheck (HTTP + Static + App service)${RESET}"
  echo
  local ip
  ip="$(get_public_ip)"

  echo -e "Service ${BOLD}${SERVICE_APP}${RESET}: $(service_status_line "$SERVICE_APP")"
  echo -e "Nginx: $(service_status_line nginx)"
  echo -e "Postgres: $(service_status_line postgresql)"
  echo -e "Redis: $(service_status_line redis-server)"
  echo

  if have curl; then
    info "Checking HTTPS: https://${DOMAIN_MAIN}"
    curl -fsSI "https://${DOMAIN_MAIN}" | head -n 5 || warn "Main page not responding."

    info "Checking main CSS: https://${DOMAIN_MAIN}/static/css/output.css"
    curl -fsSI "https://${DOMAIN_MAIN}/static/css/output.css" | head -n 5 || warn "output.css not reachable (maybe not built/collected)."

    info "Checking admin CSS (control): https://${DOMAIN_MAIN}/static/admin/css/base.css"
    curl -fsSI "https://${DOMAIN_MAIN}/static/admin/css/base.css" | head -n 5 || warn "admin css not reachable (nginx alias issue)."
  else
    warn "curl not installed; skipping HTTP checks."
  fi

  echo
  info "Tip: If admin works but main CSS fails -> run: css build + collectstatic"
  echo -e "${DIM}  1) npm run css:build\n  2) python manage.py collectstatic --noinput --settings=${DJANGO_SETTINGS}${RESET}"
  pause
}

# ------------------------------ Main Menu -------------------------------------
menu() {
  while true; do
    dashboard
    echo -e "${BOLD}Menu${RESET}"
    echo -e "${CYAN} 1${RESET}) One-click Deploy (full)"
    echo -e "${CYAN} 2${RESET}) Build Tailwind CSS (css:build)"
    echo -e "${CYAN} 3${RESET}) Django migrate"
    echo -e "${CYAN} 4${RESET}) Django collectstatic"
    echo -e "${CYAN} 5${RESET}) Restart app + nginx"
    echo -e "${CYAN} 6${RESET}) Logs viewer"
    echo -e "${CYAN} 7${RESET}) Healthcheck (site/static/app)"
    echo -e "${CYAN} 8${RESET}) Fix static/media permissions"
    echo -e "${CYAN} 9${RESET}) Edit Nginx site (with test+reload)"
    echo -e "${CYAN}10${RESET}) SSL renew (certbot dry-run)"
    echo -e "${CYAN}11${RESET}) Backup Postgres DB"
    echo -e "${CYAN}12${RESET}) Deep status checks"
    echo -e "${CYAN}13${RESET}) Tailwind watch (dev)"
    echo -e "${CYAN} 0${RESET}) Exit"
    echo
    read -r -p "Choose: " choice

    case "$choice" in
      1) action_deploy_full ;;
      2) action_build_css ;;
      3) action_django_migrate ;;
      4) action_collectstatic ;;
      5) action_restart_services ;;
      6) action_logs ;;
      7) action_healthcheck ;;
      8) action_fix_permissions ;;
      9) action_nginx_edit ;;
      10) action_certbot_renew ;;
      11) action_backup_db ;;
      12) action_status_deep ;;
      13) action_build_css_watch ;;
      0) title; ok "Bye 👋"; exit 0 ;;
      *) warn "Invalid choice"; pause ;;
    esac
  done
}

# ------------------------------ Entrypoint ------------------------------------
require_root

# Quick sanity checks
if [[ ! -d "$PROJECT_DIR" ]]; then
  err "Project directory not found: $PROJECT_DIR"
  exit 1
fi
if [[ ! -f "$MANAGE" ]]; then
  err "Django manage.py not found: $MANAGE"
  exit 1
fi

menu
