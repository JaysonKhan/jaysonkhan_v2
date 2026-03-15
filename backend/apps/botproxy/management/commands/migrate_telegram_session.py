"""Migrate file-based Telethon session to StringSession in PostgreSQL.

One-time command: eski SQLite .session faylini o'qib, StringSession
formatida PostgreSQL ga saqlaydi. Gunicorn multi-worker muhitida
ishlash uchun kerak.

Usage:
    python manage.py migrate_telegram_session
    python manage.py migrate_telegram_session --check
"""
from __future__ import annotations

import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Migrate file-based Telethon session to StringSession in PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Only check — don't migrate",
        )

    def handle(self, *args, **options):
        from botproxy.models import TelegramSession

        # Check if already migrated
        existing = TelegramSession.get_session_string()
        if existing:
            self.stdout.write(self.style.SUCCESS(
                "PostgreSQL da session mavjud (allaqachon migrate qilingan)"
            ))
            if options["check"]:
                return
            self.stdout.write("Eski sessionni yangilash uchun davom etilmoqda...")

        api_id = getattr(settings, "TELEGRAM_API_ID", 0)
        api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
        session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")

        if not api_id or not api_hash:
            self.stderr.write(self.style.ERROR(
                "TELEGRAM_API_ID yoki TELEGRAM_API_HASH sozlanmagan"
            ))
            return

        if not session_path:
            self.stderr.write(self.style.ERROR(
                "TELEGRAM_SESSION_PATH sozlanmagan"
            ))
            return

        if options["check"]:
            self.stdout.write(f"Session path: {session_path}")
            self.stdout.write("Migrate qilish uchun --check siz ishga tushiring")
            return

        self.stdout.write(f"Session fayl: {session_path}")
        self.stdout.write("Fayldan StringSession ga migrate qilinmoqda...")

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self._extract_session(api_id, api_hash, session_path)
            )
            if not result:
                self.stderr.write(self.style.ERROR("Migrate qilib bo'lmadi"))
                return

            string_session, account_id, account_name = result

            # Save to PostgreSQL (sync context — Django ORM works fine here)
            TelegramSession.save_session(
                session_string=string_session,
                account_id=account_id,
                account_name=account_name,
            )
            self.stdout.write(self.style.SUCCESS("PostgreSQL ga saqlandi"))
            self.stdout.write(self.style.SUCCESS("Muvaffaqiyatli migrate qilindi!"))
        finally:
            loop.close()

    async def _extract_session(
        self, api_id: int, api_hash: str, session_path: str
    ) -> tuple[str, int, str] | None:
        """Extract StringSession from file-based session (async).

        Returns (string_session, account_id, account_name) or None on failure.
        Django ORM calls are NOT made here — only Telethon operations.
        """
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        # 1. Open file-based session
        client = TelegramClient(session_path, api_id, api_hash)
        try:
            await client.connect()

            if not await client.is_user_authorized():
                self.stderr.write(self.style.ERROR(
                    "Session fayl mavjud, lekin avtorizatsiya qilinmagan"
                ))
                return None

            me = await client.get_me()
            self.stdout.write(f"Account: {me.first_name} @{me.username} (ID: {me.id})")

            # 2. Export session data to StringSession format
            string_session = StringSession.save(client.session)
            self.stdout.write(f"StringSession uzunligi: {len(string_session)} belgi")

            # 3. Verify the string session works
            test_client = TelegramClient(StringSession(string_session), api_id, api_hash)
            await test_client.connect()
            if await test_client.is_user_authorized():
                test_me = await test_client.get_me()
                self.stdout.write(self.style.SUCCESS(
                    f"StringSession ishlayapti! Account: {test_me.first_name}"
                ))
            else:
                self.stderr.write(self.style.ERROR("StringSession avtorizatsiya qilinmagan"))
                await test_client.disconnect()
                return None
            await test_client.disconnect()

            account_name = f"{me.first_name or ''} @{me.username or me.id}"
            return string_session, me.id, account_name

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Xatolik: {e}"))
            return None
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
