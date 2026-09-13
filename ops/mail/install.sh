#!/usr/bin/env bash
# Run ONLY through ./deploy.sh --mail. No portfolio or vendor-core deployment.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || exit 1
release=${1:?Commit SHA required}
[[ $release =~ ^[0-9a-f]{40}$ ]] || exit 1
source_dir=$(cd "$(dirname "$0")" && pwd)
mail_root=/var/www/roundcube
private=/var/lib/jaysonkhan-mail
db=$mail_root/db/roundcube.db
[[ -d $mail_root && ! -L $mail_root ]] || exit 1
# Historical name: BOTH mail tenants must serialize shared config/SQLite writes.
exec 9>/run/lock/uzexam-mail-deploy.lock
flock -n 9 || { echo 'Another mail deploy is active'; exit 1; }
version=$(sed -n "s/define('RCMAIL_VERSION', '\([^']*\)').*/\1/p" "$mail_root/program/include/iniset.php")
[[ $version == 1.6.19 ]] || { echo 'Unreviewed Roundcube version; stop for compatibility audit'; exit 1; }
[[ $(sqlite3 "$db" 'pragma integrity_check;') == ok ]] || exit 1
[[ $(sqlite3 "$db" "select value from system where name='roundcube-version';") == 2022081200 ]] || exit 1
nginx -t
systemctl is-active --quiet postfix@- dovecot php8.3-fpm nginx
openssl s_client -connect 127.0.0.1:993 -servername mail.jaysonkhan.com \
  -verify_hostname mail.jaysonkhan.com -verify_return_error </dev/null >/dev/null 2>&1
# configure.py uses the already-installed privacy-preserving log format.
grep -Rq 'log_format uzexam_safe' /etc/nginx/conf.d
while IFS= read -r file; do php -l "$file" >/dev/null; done < <(find "$source_dir" -type f \( -name '*.php' -o -name '*.inc' \))
php "$source_dir/tests/native_from.php" "$mail_root"
stamp=$(date -u +%Y%m%dT%H%M%SZ)-${release:0:12}
backup=/var/backups/jaysonkhan-mail/$stamp
install -d -m 700 "$backup"
cp -a "$mail_root/config/config.inc.php" "$backup/config.inc.php"
cp -a /etc/nginx/sites-available/mail.jaysonkhan.com "$backup/nginx.conf"
sqlite3 "$db" ".backup '$backup/roundcube.db'"
if [[ -d $mail_root/plugins/jaysonkhan_mail ]]; then
  cp -a "$mail_root/plugins/jaysonkhan_mail" "$backup/plugin"
fi
if [[ -f $mail_root/config/jaysonkhan-mail.inc.php ]]; then
  cp -a "$mail_root/config/jaysonkhan-mail.inc.php" "$backup/host.inc.php"
fi
if [[ -d $private ]]; then cp -a "$private" "$backup/private"; fi
# Prove that the sibling plugin/config/release and vendor runtime are unchanged.
find "$mail_root/plugins/uzexam_mail" "$mail_root/program" "$mail_root/vendor" -type f -print0 \
  | sort -z | xargs -0 sha256sum > "$backup/untouched.sha256"
sha256sum "$mail_root/config/uzexam-mail.inc.php" /var/lib/uzexam-mail/RELEASE >> "$backup/untouched.sha256"
echo "Restore point: $backup"
restore_on_error() {
  rc=$?; trap - ERR
  echo "Release failed. Restoring Jayson code/config; live database is NOT overwritten." >&2
  cp -a "$backup/config.inc.php" "$mail_root/config/config.inc.php"
  cp -a "$backup/nginx.conf" /etc/nginx/sites-available/mail.jaysonkhan.com
  if [[ -d $mail_root/plugins/jaysonkhan_mail ]]; then
    mv "$mail_root/plugins/jaysonkhan_mail" "$backup/failed-plugin"
  fi
  if [[ -d $backup/plugin ]]; then cp -a "$backup/plugin" "$mail_root/plugins/jaysonkhan_mail"; fi
  if [[ -f $backup/host.inc.php ]]; then cp -a "$backup/host.inc.php" "$mail_root/config/jaysonkhan-mail.inc.php"; fi
  if [[ -d $private ]]; then mv "$private" "$backup/failed-private"; fi
  if [[ -d $backup/private ]]; then cp -a "$backup/private" "$private"; fi
  nginx -t && systemctl reload nginx
  systemctl reload php8.3-fpm
  exit "$rc"
}
trap restore_on_error ERR
install -d -m 750 -o root -g www-data "$private"
rsync -a "$source_dir/jaysonkhan_mail/" "$mail_root/plugins/jaysonkhan_mail/"
chown -R root:www-data "$mail_root/plugins/jaysonkhan_mail"
find "$mail_root/plugins/jaysonkhan_mail" -type d -exec chmod 755 '{}' +
find "$mail_root/plugins/jaysonkhan_mail" -type f -exec chmod 644 '{}' +
install -m 640 -o root -g www-data "$source_dir/config.inc.php" "$mail_root/config/jaysonkhan-mail.inc.php"
python3 "$source_dir/configure.py"
python3 "$source_dir/sync_identities.py" --db "$db" --aliases "$private/aliases.json" --apply
nginx -t
systemctl reload nginx
systemctl reload php8.3-fpm
sha256sum --check --status "$backup/untouched.sha256"
[[ $(sqlite3 "$db" 'pragma integrity_check;') == ok ]] || false
systemctl is-active --quiet postfix@- dovecot php8.3-fpm nginx
for host in mail.jaysonkhan.com mail.uzexam.uz; do
  curl --fail --silent --show-error --max-time 20 "https://$host/" -o "$backup/$host.html"
  grep -q 'id="login-form"' "$backup/$host.html"
done
grep -q 'plugins/jaysonkhan_mail/mail.css' "$backup/mail.jaysonkhan.com.html"
grep -q 'plugins/uzexam_mail/mail.css' "$backup/mail.uzexam.uz.html"
! grep -q 'plugins/uzexam_mail/mail.css' "$backup/mail.jaysonkhan.com.html" || false
! grep -q 'plugins/jaysonkhan_mail/mail.css' "$backup/mail.uzexam.uz.html" || false
printf '%s\n' "$release" > "$private/RELEASE"
chmod 644 "$private/RELEASE"
trap - ERR
echo "Jayson mail verified: $release. Vendor, UzExam, mail routing and portfolio unchanged."
