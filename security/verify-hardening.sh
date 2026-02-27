#!/usr/bin/env bash
# ==============================================================================
# Jaysonkhan Security Verification Script
# Validates ALL hardening measures from the security audit
#
# Usage: ssh jaysonkhan 'bash -s' < security/verify-hardening.sh
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

PASS=0
FAIL=0
WARN=0

check_pass() { echo -e "${GREEN}${BOLD}  ✔ PASS${RESET} $*"; ((PASS++)); }
check_fail() { echo -e "${RED}${BOLD}  ✖ FAIL${RESET} $*"; ((FAIL++)); }
check_warn() { echo -e "${YELLOW}${BOLD}  ⚠ WARN${RESET} $*"; ((WARN++)); }

echo
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🔍 Jaysonkhan Security Verification${RESET}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo

# ==============================================================================
# S: SERVER HARDENING CHECKS
# ==============================================================================
echo -e "${BOLD}[S] Server Hardening${RESET}"
echo -e "────────────────────────────────────────────────────────────"

# S01: SSH port
ACTIVE_SSH_PORT=$(ss -tlnp 2>/dev/null | grep sshd | awk '{print $4}' | grep -oE '[0-9]+$' | head -1)
if [[ "$ACTIVE_SSH_PORT" != "22" && -n "$ACTIVE_SSH_PORT" ]]; then
    check_pass "S01: SSH not on default port 22 (port: $ACTIVE_SSH_PORT)"
else
    check_fail "S01: SSH still on default port 22"
fi

# S02: Root login disabled
ROOT_LOGIN=$(grep -i "^PermitRootLogin" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | tail -1 | awk '{print $2}')
if [[ "$ROOT_LOGIN" == "no" ]]; then
    check_pass "S02: Root SSH login disabled"
else
    check_fail "S02: Root SSH login NOT disabled (value: $ROOT_LOGIN)"
fi

# S03: Password auth disabled
PWD_AUTH=$(grep -i "^PasswordAuthentication" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | tail -1 | awk '{print $2}')
if [[ "$PWD_AUTH" == "no" ]]; then
    check_pass "S03: Password authentication disabled"
else
    check_fail "S03: Password authentication NOT disabled (value: $PWD_AUTH)"
fi

# S04: Fail2ban active
if systemctl is-active fail2ban &>/dev/null; then
    F2B_JAILS=$(fail2ban-client status 2>/dev/null | grep "Jail list" | awk -F: '{print $2}' | tr -d ' ')
    check_pass "S04: Fail2Ban active (jails: $F2B_JAILS)"
else
    check_fail "S04: Fail2Ban not active"
fi

# S05: Firewall enabled
if ufw status 2>/dev/null | grep -q "Status: active"; then
    ALLOWED=$(ufw status 2>/dev/null | grep "ALLOW" | wc -l)
    check_pass "S05: UFW firewall active ($ALLOWED rules)"
else
    check_fail "S05: UFW firewall not active"
fi

# S06: Auto-updates
if systemctl is-active unattended-upgrades &>/dev/null; then
    check_pass "S06: Automatic security updates enabled"
else
    check_fail "S06: Automatic updates not configured"
fi

# S07: Unnecessary services
for svc in avahi-daemon cups bluetooth ModemManager; do
    if systemctl is-active "$svc" &>/dev/null 2>&1; then
        check_warn "S07: Unnecessary service running: $svc"
    fi
done
check_pass "S07: Unnecessary services check complete"

# S08: Auditd
if systemctl is-active auditd &>/dev/null; then
    RULES=$(auditctl -l 2>/dev/null | wc -l)
    check_pass "S08: Auditd active ($RULES rules loaded)"
else
    check_fail "S08: Auditd not active"
fi

# S09: Sysctl hardening
SYNCOOKIES=$(sysctl -n net.ipv4.tcp_syncookies 2>/dev/null)
ASLR=$(sysctl -n kernel.randomize_va_space 2>/dev/null)
if [[ "$SYNCOOKIES" == "1" && "$ASLR" == "2" ]]; then
    check_pass "S09: Kernel hardening params applied (syncookies=$SYNCOOKIES, ASLR=$ASLR)"
else
    check_fail "S09: Kernel hardening params missing (syncookies=$SYNCOOKIES, ASLR=$ASLR)"
fi

# S10: SUID/SGID check
SUID_COUNT=$(find / -perm /6000 -type f 2>/dev/null | wc -l)
if [[ "$SUID_COUNT" -lt 30 ]]; then
    check_pass "S10: SUID/SGID binaries count acceptable ($SUID_COUNT)"
else
    check_warn "S10: High number of SUID/SGID binaries ($SUID_COUNT) — review recommended"
fi

echo

# ==============================================================================
# W: WEB SERVER CHECKS
# ==============================================================================
echo -e "${BOLD}[W] Web Server (Nginx/TLS)${RESET}"
echo -e "────────────────────────────────────────────────────────────"

DOMAIN="jaysonkhan.com"

# W01: TLS version check
if command -v openssl &>/dev/null; then
    TLS10=$(echo | timeout 5 openssl s_client -connect $DOMAIN:443 -tls1 2>&1 || true)
    if echo "$TLS10" | grep -q "alert protocol version\|no protocols"; then
        check_pass "W01: TLS 1.0 disabled"
    else
        check_fail "W01: TLS 1.0 still enabled"
    fi

    TLS12=$(echo | timeout 5 openssl s_client -connect $DOMAIN:443 -tls1_2 2>&1 || true)
    if echo "$TLS12" | grep -q "CONNECTED"; then
        check_pass "W01: TLS 1.2 enabled"
    fi
fi

# W02: HSTS header
if command -v curl &>/dev/null; then
    HSTS=$(curl -sI "https://$DOMAIN" 2>/dev/null | grep -i "strict-transport-security" | head -1)
    if [[ -n "$HSTS" ]]; then
        check_pass "W02: HSTS header present ($HSTS)"
    else
        check_fail "W02: HSTS header missing"
    fi

    # W03: CSP header
    CSP=$(curl -sI "https://$DOMAIN" 2>/dev/null | grep -i "content-security-policy" | head -1)
    if [[ -n "$CSP" ]]; then
        check_pass "W03: CSP header present"
    else
        check_fail "W03: CSP header missing"
    fi

    # W04: Server version hidden
    SVR=$(curl -sI "https://$DOMAIN" 2>/dev/null | grep -i "^Server:" | head -1)
    if echo "$SVR" | grep -qiE "nginx/[0-9]|apache/[0-9]"; then
        check_fail "W04: Server version exposed ($SVR)"
    else
        check_pass "W04: Server version hidden ($SVR)"
    fi

    # W05: Rate limiting
    RATE_FAIL=0
    for i in $(seq 1 30); do
        CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/api/" 2>/dev/null || echo 000)
        if [[ "$CODE" == "429" || "$CODE" == "503" ]]; then
            RATE_FAIL=1
            break
        fi
    done
    if [[ $RATE_FAIL -eq 1 ]]; then
        check_pass "W05: Rate limiting active (got 429 after rapid requests)"
    else
        check_warn "W05: Rate limiting may not be working (no 429 after 30 requests)"
    fi

    # W06: Directory listing disabled
    DIR_LIST=$(curl -s "https://$DOMAIN/static/" 2>/dev/null | grep -ci "index of" || true)
    if [[ "$DIR_LIST" -eq 0 ]]; then
        check_pass "W06: Directory listing disabled"
    else
        check_fail "W06: Directory listing enabled!"
    fi

    # W07: HTTP redirects to HTTPS
    HTTP_LOC=$(curl -sI "http://$DOMAIN" 2>/dev/null | grep -i "location" | head -1)
    if echo "$HTTP_LOC" | grep -qi "https://"; then
        check_pass "W07: HTTP → HTTPS redirect working"
    else
        check_fail "W07: HTTP not redirecting to HTTPS"
    fi

    # W08: X-Content-Type-Options
    XCTO=$(curl -sI "https://$DOMAIN" 2>/dev/null | grep -i "x-content-type-options" | head -1)
    if echo "$XCTO" | grep -qi "nosniff"; then
        check_pass "W08: X-Content-Type-Options: nosniff present"
    else
        check_fail "W08: X-Content-Type-Options header missing"
    fi
fi

echo

# ==============================================================================
# A: APPLICATION SECURITY CHECKS
# ==============================================================================
echo -e "${BOLD}[A] Application Security${RESET}"
echo -e "────────────────────────────────────────────────────────────"

if command -v curl &>/dev/null; then
    # A01: SQL Injection test
    SQLI=$(curl -s "https://$DOMAIN/api/projects/?id=1'OR'1'='1" 2>/dev/null)
    if echo "$SQLI" | grep -qiE "error|traceback|sql|syntax"; then
        check_fail "A01: Possible SQL injection (error details leaked)"
    else
        check_pass "A01: SQL injection test — no error leakage"
    fi

    # A02: XSS test
    XSS=$(curl -s "https://$DOMAIN/blog/?q=<script>alert(1)</script>" 2>/dev/null)
    if echo "$XSS" | grep -q "<script>alert(1)</script>"; then
        check_fail "A02: XSS reflected (unescaped script tag in response)"
    else
        check_pass "A02: XSS test — script tag not reflected"
    fi

    # A03: CSRF presence
    CSRF=$(curl -s "https://$DOMAIN/contact/" 2>/dev/null | grep -ci "csrfmiddlewaretoken" || true)
    if [[ "$CSRF" -gt 0 ]]; then
        check_pass "A03: CSRF token present in contact form"
    else
        check_warn "A03: CSRF token not found in contact form"
    fi

    # A04: Path traversal
    PT=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/media/../../etc/passwd" 2>/dev/null || echo 000)
    if [[ "$PT" != "200" ]]; then
        check_pass "A04: Path traversal blocked (HTTP $PT)"
    else
        check_fail "A04: Path traversal may be possible!"
    fi

    # A05: SSRF test
    SSRF=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/api/?url=http://169.254.169.254/" 2>/dev/null || echo 000)
    if [[ "$SSRF" != "200" ]]; then
        check_pass "A05: SSRF metadata endpoint not accessible"
    else
        check_fail "A05: SSRF may be possible (metadata endpoint returned 200)"
    fi

    # A06: Admin panel discoverability
    ADMIN_DEFAULT=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/admin/" 2>/dev/null || echo 000)
    if [[ "$ADMIN_DEFAULT" == "404" || "$ADMIN_DEFAULT" == "444" ]]; then
        check_pass "A08: Admin panel not at /admin/ (HTTP $ADMIN_DEFAULT)"
    else
        check_fail "A08: Admin panel discoverable at /admin/ (HTTP $ADMIN_DEFAULT)"
    fi

    # A07: Django debug mode
    DEBUG_CHECK=$(curl -s "https://$DOMAIN/nonexistent-page-xyz/" 2>/dev/null)
    if echo "$DEBUG_CHECK" | grep -qiE "traceback|stack trace|settings\.py|INSTALLED_APPS"; then
        check_fail "A07: Django DEBUG mode appears to be ON (traceback visible)"
    else
        check_pass "A07: Django DEBUG mode OFF (no traceback in errors)"
    fi
fi

echo

# ==============================================================================
# D: DATA SECURITY CHECKS
# ==============================================================================
echo -e "${BOLD}[D] Data Security${RESET}"
echo -e "────────────────────────────────────────────────────────────"

# D01: .env file permissions
if [[ -f /var/www/jaysonkhan/.env ]]; then
    ENV_PERMS=$(stat -c "%a" /var/www/jaysonkhan/.env 2>/dev/null || stat -f "%Lp" /var/www/jaysonkhan/.env 2>/dev/null)
    if [[ "$ENV_PERMS" -le 640 ]]; then
        check_pass "D01: .env file permissions restrictive ($ENV_PERMS)"
    else
        check_fail "D01: .env file too permissive ($ENV_PERMS) — should be 640 or less"
    fi
fi

# D02: .env not in git
if [[ -d /var/www/jaysonkhan/.git ]]; then
    if git -C /var/www/jaysonkhan ls-files --cached 2>/dev/null | grep -q "^\.env$"; then
        check_fail "D02: .env file is tracked by git!"
    else
        check_pass "D02: .env file not tracked by git"
    fi
fi

# D03: Database connection
if command -v psql &>/dev/null; then
    PG_SSL=$(psql -h 127.0.0.1 -U portfolio_user -d portfolio_db -c "SHOW ssl;" 2>/dev/null | grep -c "on" || echo 0)
    if [[ "$PG_SSL" -gt 0 ]]; then
        check_pass "D03: PostgreSQL SSL connections enabled"
    else
        check_warn "D03: PostgreSQL SSL may not be enabled for local connections"
    fi
fi

# D04: Backup directory permissions
if [[ -d /var/backups/jaysonkhan ]]; then
    BACKUP_PERMS=$(stat -c "%a" /var/backups/jaysonkhan 2>/dev/null || stat -f "%Lp" /var/backups/jaysonkhan 2>/dev/null)
    if [[ "$BACKUP_PERMS" -le 750 ]]; then
        check_pass "D04: Backup directory permissions ok ($BACKUP_PERMS)"
    else
        check_warn "D04: Backup directory may be too open ($BACKUP_PERMS)"
    fi
fi

echo

# ==============================================================================
# SUMMARY
# ==============================================================================
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
TOTAL=$((PASS + FAIL + WARN))
echo -e "${BOLD}Results: ${GREEN}$PASS PASS${RESET} | ${RED}$FAIL FAIL${RESET} | ${YELLOW}$WARN WARN${RESET} | Total: $TOTAL"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}${BOLD}❌ Security verification has $FAIL failures. Address them immediately.${RESET}"
    exit 1
else
    echo -e "${GREEN}${BOLD}✅ All critical checks passed!${RESET}"
fi
