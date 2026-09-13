"""Provision send-as profiles from the private, authoritative receiving map.

Only adds missing active aliases to existing JaysonKhan users. Never modifies a
profile, signature, default sender, preference, credential or another domain.
BEGIN IMMEDIATE makes parallel invocations idempotent on this SQLite deployment.
Run after configure.py and after the installer's consistent database backup.
"""
import argparse
import json
from pathlib import Path
import re
import sqlite3


ADDRESS = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@jaysonkhan\.com", re.I)


def address(value):
    if not isinstance(value, str) or not ADDRESS.fullmatch(value) or len(value) > 128:
        raise ValueError('Invalid JaysonKhan address in private alias map')
    return value.lower()


def sync(db_path, alias_path, apply=False):
    raw = json.loads(Path(alias_path).read_text())
    if not isinstance(raw, dict):
        raise ValueError('Alias map must be an object')
    mapping = {}
    for mailbox, aliases in raw.items():
        if not isinstance(aliases, list):
            raise ValueError('Alias list required')
        mapping[address(mailbox)] = sorted({address(alias) for alias in aliases} - {address(mailbox)})
    # mode=rw prevents a typo from silently creating a new empty database.
    db = sqlite3.connect(Path(db_path).resolve().as_uri() + '?mode=rw', uri=True, timeout=15)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT value FROM system WHERE name='roundcube-version'").fetchone() != ('2022081200',):
            raise ValueError('Unexpected Roundcube schema')
        created = 0
        for user_id, username in db.execute("SELECT user_id, username FROM users WHERE mail_host='127.0.0.1'"):
            # Receiving ownership is backend-specific. Also ensure a legitimate
            # primary profile exists without rewriting historical sender data.
            if username.lower() not in mapping:
                continue
            aliases = [username.lower()] + mapping[username.lower()]
            existing = {row[0].lower() for row in db.execute(
                'SELECT email FROM identities WHERE user_id=? AND del=0', (user_id,))}
            for alias in aliases:
                if alias not in existing:
                    db.execute("INSERT INTO identities (user_id, email, name, standard, changed) VALUES (?, ?, '', 0, datetime('now'))", (user_id, alias))
                    existing.add(alias)
                    created += 1
        if apply:
            db.commit()
        else:
            db.rollback()
        return created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--aliases', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    count = sync(args.db, args.aliases, args.apply)
    print(f"Sender profiles {'created' if args.apply else 'planned'}: {count}")
