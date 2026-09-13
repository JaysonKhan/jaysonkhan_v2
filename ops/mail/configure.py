"""Idempotent, narrowly scoped config transformation. No secrets in stdout."""
import json
import re
from pathlib import Path
import os
import subprocess

INCLUDE = "require __DIR__ . '/jaysonkhan-mail.inc.php';"


def include_config(text):
    if INCLUDE in text:
        return text
    text = re.sub(r'\?>\s*$', '', text)
    return text.rstrip() + '\n\n// Managed by JaysonKhan ops/mail; keep existing credentials and per-host config.\n' + INCLUDE + '\n'


def safe_log(text):
    if 'access_log /var/log/nginx/access.log uzexam_safe;' in text:
        return text
    # Existing mail vhost has exactly the two inspected HTTP/HTTPS blocks.
    if text.count('server {') != 2 or 'server_name mail.jaysonkhan.com;' not in text:
        raise ValueError('Unexpected mail vhost structure; manual review required')
    return text.replace('server {', 'server {\n    access_log /var/log/nginx/access.log uzexam_safe;')


def alias_map(aliases, mailboxes):
    """Grant exact aliases with ONE unambiguous local owner.

    Fan-out, external endpoints and cycles are not evidence of exclusive send
    ownership. They remain operational in Postfix but require explicit review.
    """
    routes = {}
    for line in aliases.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            routes[parts[0].lower()] = [s.strip().lower() for s in parts[1].split(',')]
    boxes = {line.split()[0].lower() for line in mailboxes.splitlines() if line.split()}
    result = {box: [] for box in boxes if box.endswith('@jaysonkhan.com')}

    def destinations(address, visited):
        if address in visited:
            return {'!cycle'}
        if address in routes:
            return set().union(*(destinations(x, visited | {address}) for x in routes[address]))
        return {address}

    for address in sorted(routes):
        if not re.fullmatch(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@jaysonkhan\.com', address):
            continue
        owners = destinations(address, set())
        if len(owners) != 1:
            continue
        for box in owners:
            if box in result and box != address:
                result[box].append(address)
    return result


def atomic_write(path, value, mode, group=0):
    target = Path(path)
    temporary = target.with_name(target.name + '.jaysonkhan-new')
    # Reject symlinks before writing a predictable temporary filename as root.
    if temporary.is_symlink():
        raise ValueError('Refusing symlink temporary file')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.chown(temporary, 0, group)
    os.chmod(temporary, mode)
    os.replace(temporary, target)


def configure():
    root = Path('/var/www/roundcube')
    config = root / 'config/config.inc.php'
    new = include_config(config.read_text())
    # Validate the transformed PHP before replacing the active config.
    checked = subprocess.run(['php', '-l'], input=new, text=True, capture_output=True)
    if checked.returncode:
        raise RuntimeError('Generated PHP config did not pass lint')
    aliases = subprocess.check_output(['postmap', '-s', '/etc/postfix/virtual_alias_maps'], text=True)
    mailboxes = subprocess.check_output(['postmap', '-s', '/etc/postfix/virtual_mailbox_maps'], text=True)
    mapping = alias_map(aliases, mailboxes)
    if 'admin@jaysonkhan.com' not in mapping:
        raise RuntimeError('Expected JaysonKhan mailbox missing; refusing to publish an incorrect mapping')
    atomic_write('/var/lib/jaysonkhan-mail/aliases.json', json.dumps(mapping, indent=2) + '\n', 0o640, 33)
    atomic_write(config, new, 0o640, 33)
    vhost = Path('/etc/nginx/sites-available/mail.jaysonkhan.com')
    atomic_write(vhost, safe_log(vhost.read_text()), 0o644)
    print('Mail config validated; private alias export refreshed.')


if __name__ == '__main__':
    configure()
