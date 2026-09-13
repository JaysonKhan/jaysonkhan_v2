import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

MAIL = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync_identities', MAIL / 'sync_identities.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SenderProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'test.db'
        self.aliases = Path(self.tmp.name) / 'aliases.json'
        self.aliases.write_text(json.dumps({'admin@jaysonkhan.com': ['support@jaysonkhan.com', 'HELP@jaysonkhan.com', 'support@jaysonkhan.com']}))
        with sqlite3.connect(self.db) as db:
            db.executescript("""
            CREATE TABLE system (name TEXT, value TEXT);
            INSERT INTO system VALUES ('roundcube-version', '2022081200');
            CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT, mail_host TEXT);
            INSERT INTO users VALUES (1, 'admin@jaysonkhan.com','127.0.0.1'), (2, 'admin@uzexam.uz','127.0.0.1'),
                (3,'admin@jaysonkhan.com','different.backend');
            CREATE TABLE identities (identity_id INTEGER PRIMARY KEY, user_id INTEGER,
              email TEXT, name TEXT DEFAULT '', standard INTEGER DEFAULT 0,
              del INTEGER DEFAULT 0, signature TEXT DEFAULT '', changed TEXT);
            INSERT INTO identities(user_id,email,name,standard,signature)
              VALUES (1,'admin@jaysonkhan.com','Owner',1,'Keep my signature'),
                     (2,'admin@uzexam.uz','Other host',1,'Untouched');
            """)

    def rows(self):
        with sqlite3.connect(self.db) as db:
            return db.execute('SELECT user_id,email,name,standard,signature,del FROM identities ORDER BY identity_id').fetchall()

    def test_dry_run_then_idempotent_apply_preserves_existing_records(self):
        before = self.rows()
        self.assertEqual(sync.sync(self.db, self.aliases), 2)
        self.assertEqual(self.rows(), before)
        self.assertEqual(sync.sync(self.db, self.aliases, True), 2)
        self.assertEqual(sync.sync(self.db, self.aliases, True), 0)
        self.assertEqual(self.rows()[:2], before)
        self.assertTrue(all(row[0] == 1 and row[3] == 0 for row in self.rows()[2:]))

    def test_removed_alias_is_not_deleted_and_customization_is_not_overwritten(self):
        sync.sync(self.db, self.aliases, True)
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE identities SET name='Support team', signature='Custom' WHERE email='support@jaysonkhan.com'")
        before = self.rows()
        self.aliases.write_text(json.dumps({'admin@jaysonkhan.com': []}))
        self.assertEqual(sync.sync(self.db, self.aliases, True), 0)
        self.assertEqual(self.rows(), before)

    def test_malformed_foreign_or_missing_source_fails_closed(self):
        before = self.rows()
        for invalid in [[], {'admin@jaysonkhan.com': 'not a list'}, {'admin@jaysonkhan.com': ['evil@example.org']}, {'admin@jaysonkhan.com': ['x\r\nBcc:y@jaysonkhan.com']}]:
            self.aliases.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError):
                sync.sync(self.db, self.aliases, True)
            self.assertEqual(self.rows(), before)

    def test_unknown_schema_does_not_write(self):
        before = self.rows()
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE system SET value='unknown'")
        with self.assertRaises(ValueError):
            sync.sync(self.db, self.aliases, True)
        self.assertEqual(self.rows(), before)

    def test_mid_transaction_failure_rolls_back_all_new_profiles(self):
        before = self.rows()
        with sqlite3.connect(self.db) as db:
            db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON identities WHEN NEW.email='support@jaysonkhan.com' BEGIN SELECT RAISE(ABORT, 'test'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            sync.sync(self.db, self.aliases, True)
        self.assertEqual(self.rows(), before)

    def test_legacy_foreign_default_preserved_but_own_primary_provisioned(self):
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO users VALUES (4,'jaysonkhan@jaysonkhan.com','127.0.0.1')")
            db.execute("INSERT INTO identities(user_id,email,name,standard,signature) VALUES (4,'admin@jaysonkhan.com','Legacy',1,'Keep')")
        self.aliases.write_text(json.dumps({'jaysonkhan@jaysonkhan.com': []}))
        before = self.rows()
        self.assertEqual(sync.sync(self.db, self.aliases, True), 1)
        self.assertEqual(self.rows()[:-1], before)
        self.assertEqual(self.rows()[-1][0:4], (4,'jaysonkhan@jaysonkhan.com','',0))
        self.assertEqual(sync.sync(self.db, self.aliases, True), 0)
