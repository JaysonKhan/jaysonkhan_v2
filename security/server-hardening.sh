#!/usr/bin/env bash
# ==============================================================================
# Jaysonkhan Server Hardening Script
# Ubuntu LTS — Full security hardening based on CIS Benchmark + OWASP
#
# Usage: ssh jaysonkhan 'bash -s' < security/server-hardening.sh
#
# ⚠️  Review each section before running. This modifies system configuration.
# ==============================================================================

set -Eeuo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "${GREEN}${BOLD}✔${RESET} $*"; }
warn() { echo -e "${YELLOW}${BOLD}⚠${RESET} $*"; }
err()  { echo -e "${RED}${BOLD}✖${RESET} $*"; }
info() { echo -e "${CYAN}${BOLD}ℹ${RESET} $*"; }
line() { echo -e "────────────────────────────────────────────────────────────"; }

# Require root
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    err "This script must be run as root: sudo $0"
    exit 1
fi

echo
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}🛡️  Jaysonkhan Server Hardening${RESET}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo

# ==============================================================================
# 1. SYSTEM UPDATE
# ==============================================================================
info "1/9 System Update & Essential Packages"
line

apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq \
    ufw fail2ban unattended-upgrades \
    auditd audispd-plugins \
    logrotate rsyslog \
    libpam-pwquality \
    apt-listchanges \
    rkhunter chkrootkit \
    acl net-tools

ok "System updated and essential packages installed"
echo

# ==============================================================================
# 2. SSH HARDENING
# ==============================================================================
info "2/9 SSH Hardening"
line

# Backup original SSH config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)

cat > /etc/ssh/sshd_config.d/99-hardened.conf << 'SSHEOF'
# ==============================================================================
# HARDENED SSH CONFIGURATION — jaysonkhan.com
# CIS Benchmark 5.2.x compliance
# ==============================================================================

# ── Protocol & Port ──────────────────────────────────────────────────────────
# Use non-standard port to avoid mass scanners
Port 2299
Protocol 2

# ── Authentication ───────────────────────────────────────────────────────────
# Key-only authentication, no passwords, no root login
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
AuthenticationMethods publickey

# ── Key exchange & ciphers (strong only) ─────────────────────────────────────
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp521,ecdh-sha2-nistp384,ecdh-sha2-nistp256,diffie-hellman-group-exchange-sha256
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,ssh-ed25519-cert-v01@openssh.com,rsa-sha2-512,rsa-sha2-256

# ── Session limits ───────────────────────────────────────────────────────────
MaxAuthTries 3
MaxSessions 3
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2

# ── Restriction ──────────────────────────────────────────────────────────────
X11Forwarding no
AllowTcpForwarding no
GatewayPorts no
PermitTunnel no
AllowAgentForwarding no
PermitUserEnvironment no
DisableForwarding yes

# ── Logging ──────────────────────────────────────────────────────────────────
LogLevel VERBOSE
SyslogFacility AUTH

# ── SFTP (chroot for non-admin users) ────────────────────────────────────────
Subsystem sftp /usr/lib/openssh/sftp-server

# ── Banner ───────────────────────────────────────────────────────────────────
Banner /etc/ssh/banner.txt
SSHEOF

# Create SSH banner
cat > /etc/ssh/banner.txt << 'BANNEREOF'
╔══════════════════════════════════════════════════════════════╗
║  UNAUTHORIZED ACCESS IS PROHIBITED                          ║
║  This system is monitored. All sessions are logged.         ║
║  Disconnect immediately if you are not authorized.          ║
╚══════════════════════════════════════════════════════════════╝
BANNEREOF

# Create deploy user (non-root) for SSH access
if ! id "deploy" &>/dev/null; then
    useradd -m -s /bin/bash -G sudo deploy
    mkdir -p /home/deploy/.ssh
    # Copy root's authorized_keys to deploy user
    if [[ -f /root/.ssh/authorized_keys ]]; then
        cp /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
    fi
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
    chmod 600 /home/deploy/.ssh/authorized_keys
    ok "Created 'deploy' user with SSH key access"
else
    ok "'deploy' user already exists"
fi

# Test SSH config before restarting
if sshd -t; then
    systemctl restart sshd
    ok "SSH hardened and restarted"
else
    err "SSH config test failed! Restoring backup."
    cp /etc/ssh/sshd_config.bak.$(date +%Y%m%d) /etc/ssh/sshd_config
    rm -f /etc/ssh/sshd_config.d/99-hardened.conf
    systemctl restart sshd
fi
echo

# ==============================================================================
# 3. FIREWALL (UFW)
# ==============================================================================
info "3/9 Firewall Configuration (UFW)"
line

ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH on new port
ufw allow 2299/tcp comment 'SSH (hardened port)'

# Web traffic
ufw allow 80/tcp comment 'HTTP (redirect to HTTPS)'
ufw allow 443/tcp comment 'HTTPS'

# Rate limit SSH
ufw limit 2299/tcp

# Enable
ufw --force enable

ok "Firewall configured: deny all incoming, allow 2299(SSH), 80, 443"
echo

# ==============================================================================
# 4. FAIL2BAN
# ==============================================================================
info "4/9 Fail2Ban Configuration"
line

cat > /etc/fail2ban/jail.local << 'F2BEOF'
# ==============================================================================
# Fail2Ban — Jaysonkhan Hardened Configuration
# ==============================================================================
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3
backend  = systemd
banaction = ufw

# Email notification (optional)
# destemail = admin@jaysonkhan.com
# sendername = Fail2Ban-Jaysonkhan
# mta = sendmail
# action = %(action_mwl)s

[sshd]
enabled  = true
port     = 2299
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 3
bantime  = 86400
findtime = 600

[nginx-http-auth]
enabled  = true
filter   = nginx-http-auth
logpath  = /var/log/nginx/jaysonkhan_error.log
maxretry = 3
bantime  = 3600

[nginx-limit-req]
enabled  = true
filter   = nginx-limit-req
logpath  = /var/log/nginx/jaysonkhan_error.log
maxretry = 10
bantime  = 7200

[nginx-botsearch]
enabled  = true
filter   = nginx-botsearch
logpath  = /var/log/nginx/jaysonkhan_access.log
maxretry = 5
bantime  = 86400
F2BEOF

# Custom filter for Django brute-force (optional)
cat > /etc/fail2ban/filter.d/django-login.conf << 'DLEOF'
[Definition]
failregex = Authentication failure.* from <HOST>
ignoreregex =
DLEOF

systemctl restart fail2ban
systemctl enable fail2ban
ok "Fail2Ban configured with SSH, Nginx, and custom jails"
echo

# ==============================================================================
# 5. KERNEL HARDENING (sysctl)
# ==============================================================================
info "5/9 Kernel Hardening (sysctl)"
line

cat > /etc/sysctl.d/99-security.conf << 'SYSCTLEOF'
# ==============================================================================
# Kernel Security Hardening — CIS Benchmark
# ==============================================================================

# ── Network hardening ────────────────────────────────────────────────────────
# Disable IP forwarding
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# Disable source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0

# Log martian packets (spoofed, source-routed, redirected)
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ICMP broadcast
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Reverse path filtering (anti-spoofing)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Disable IPv6 if not needed
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1

# ── Memory protection ───────────────────────────────────────────────────────
# Restrict dmesg to root
kernel.dmesg_restrict = 1

# Restrict kernel pointer exposure
kernel.kptr_restrict = 2

# Restrict ptrace scope
kernel.yama.ptrace_scope = 2

# ASLR
kernel.randomize_va_space = 2

# Restrict core dumps
fs.suid_dumpable = 0

# ── File system ──────────────────────────────────────────────────────────────
# Restrict hardlink/symlink creation
fs.protected_hardlinks = 1
fs.protected_symlinks = 1

# ── TCP performance + security ───────────────────────────────────────────────
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_keepalive_probes = 5
net.core.somaxconn = 65535
net.ipv4.tcp_rfc1337 = 1
SYSCTLEOF

sysctl --system > /dev/null 2>&1
ok "Kernel hardened (sysctl parameters applied)"
echo

# ==============================================================================
# 6. AUTOMATIC SECURITY UPDATES
# ==============================================================================
info "6/9 Automatic Security Updates"
line

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'UPDATEEOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "";
UPDATEEOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'AUTOEOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
AUTOEOF

systemctl enable unattended-upgrades
systemctl start unattended-upgrades
ok "Automatic security updates configured"
echo

# ==============================================================================
# 7. AUDIT DAEMON (auditd)
# ==============================================================================
info "7/9 Audit Daemon Configuration"
line

cat > /etc/audit/rules.d/jaysonkhan.rules << 'AUDITEOF'
# ==============================================================================
# Audit Rules — Jaysonkhan Server (CIS Benchmark)
# ==============================================================================

# Delete all existing rules
-D

# Buffer size
-b 8192

# Failure mode (1 = printk, 2 = panic)
-f 1

# ── Identity changes ────────────────────────────────────────────────────────
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/gshadow -p wa -k identity
-w /etc/sudoers -p wa -k sudoers
-w /etc/sudoers.d/ -p wa -k sudoers

# ── SSH configuration changes ────────────────────────────────────────────────
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /etc/ssh/sshd_config.d/ -p wa -k sshd_config

# ── Network configuration ───────────────────────────────────────────────────
-w /etc/hosts -p wa -k hosts
-w /etc/resolv.conf -p wa -k resolv
-w /etc/hostname -p wa -k hostname

# ── System time changes ─────────────────────────────────────────────────────
-a always,exit -F arch=b64 -S adjtimex -S settimeofday -k time-change
-w /etc/localtime -p wa -k time-change

# ── Privileged commands ──────────────────────────────────────────────────────
-a always,exit -F arch=b64 -S execve -F euid=0 -k privileged

# ── File deletion monitoring ────────────────────────────────────────────────
-a always,exit -F arch=b64 -S unlink -S unlinkat -S rename -S renameat -F auid>=1000 -F auid!=4294967295 -k delete

# ── Django project files ────────────────────────────────────────────────────
-w /var/www/jaysonkhan/.env -p rwa -k jaysonkhan_env
-w /var/www/jaysonkhan/backend/config/settings/ -p wa -k jaysonkhan_settings

# ── Nginx configuration ─────────────────────────────────────────────────────
-w /etc/nginx/ -p wa -k nginx_config

# ── Make rules immutable (must be last rule) ─────────────────────────────────
-e 2
AUDITEOF

# Reload audit rules
if command -v augenrules &>/dev/null; then
    augenrules --load
fi
systemctl restart auditd
systemctl enable auditd
ok "Audit daemon configured with security rules"
echo

# ==============================================================================
# 8. LOG ROTATION
# ==============================================================================
info "8/9 Log Rotation Configuration"
line

cat > /etc/logrotate.d/jaysonkhan << 'LOGEOF'
/var/www/jaysonkhan/backend/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload jaysonkhan >/dev/null 2>&1 || true
    endscript
}

/var/log/nginx/jaysonkhan_*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx >/dev/null 2>&1 || true
    endscript
}
LOGEOF

ok "Log rotation configured for Django and Nginx logs"
echo

# ==============================================================================
# 9. FILE PERMISSIONS & CLEANUP
# ==============================================================================
info "9/9 File Permissions & System Cleanup"
line

# Set proper permissions on project directory
chown -R deploy:www-data /var/www/jaysonkhan
chmod -R 750 /var/www/jaysonkhan
chmod 640 /var/www/jaysonkhan/.env 2>/dev/null || true
chmod 640 /var/www/jaysonkhan/backend/.env 2>/dev/null || true

# Ensure media/static directories are writable by www-data
chmod -R 755 /var/www/jaysonkhan/static 2>/dev/null || true
chmod -R 755 /var/www/jaysonkhan/media 2>/dev/null || true

# Find and report SUID/SGID binaries
info "Scanning for SUID/SGID binaries..."
find / -perm /6000 -type f 2>/dev/null | head -20 > /tmp/suid_report.txt
SUID_COUNT=$(wc -l < /tmp/suid_report.txt)
warn "Found $SUID_COUNT SUID/SGID binaries. Review: /tmp/suid_report.txt"

# Disable unnecessary services
for svc in avahi-daemon cups bluetooth ModemManager; do
    if systemctl is-active "$svc" &>/dev/null; then
        systemctl stop "$svc" 2>/dev/null || true
        systemctl disable "$svc" 2>/dev/null || true
        ok "Disabled unnecessary service: $svc"
    fi
done

# Set restrictive umask
echo "umask 027" >> /etc/profile.d/umask.sh

# Generate DH params for Nginx (if not exists)
if [[ ! -f /etc/nginx/dhparam.pem ]]; then
    info "Generating DH parameters (this may take a few minutes)..."
    openssl dhparam -out /etc/nginx/dhparam.pem 2048
    ok "DH parameters generated"
fi

ok "File permissions secured"
echo

# ==============================================================================
# SUMMARY
# ==============================================================================
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}✅ Server Hardening Complete!${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo
warn "⚠️  IMPORTANT POST-HARDENING STEPS:"
echo -e "  1. ${BOLD}Update SSH config on your Mac:${RESET}"
echo -e "     Host jaysonkhan"
echo -e "         HostName 144.91.69.225"
echo -e "         User deploy"
echo -e "         Port 2299"
echo -e "         IdentityFile ~/.ssh/id_ed25519"
echo -e "         IdentitiesOnly yes"
echo
echo -e "  2. ${BOLD}Test SSH access BEFORE closing this session:${RESET}"
echo -e "     ssh -p 2299 deploy@144.91.69.225"
echo
echo -e "  3. ${BOLD}Deploy Nginx config:${RESET}"
echo -e "     cp security/nginx/jaysonkhan.conf /etc/nginx/sites-available/jaysonkhan"
echo -e "     nginx -t && systemctl reload nginx"
echo
echo -e "  4. ${BOLD}Run verification:${RESET}"
echo -e "     bash security/verify-hardening.sh"
echo
