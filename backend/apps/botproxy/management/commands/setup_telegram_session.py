"""Interactive Telethon session setup for MTProto API authentication.

Usage:
    python manage.py setup_telegram_session           # yangi session yaratish
    python manage.py setup_telegram_session --check   # mavjud sessionni tekshirish
"""
import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Telegram MTProto API uchun Telethon session sozlash"

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Faqat mavjud session haqiqiyligini tekshirish",
        )

    def handle(self, *args, **options):
        api_id = getattr(settings, "TELEGRAM_API_ID", 0)
        api_hash = getattr(settings, "TELEGRAM_API_HASH", "")
        session_path = getattr(settings, "TELEGRAM_SESSION_PATH", "")

        if not api_id or not api_hash:
            self.stderr.write(self.style.ERROR(
                "TELEGRAM_API_ID va TELEGRAM_API_HASH .env da sozlanmagan.\n"
                "https://my.telegram.org/apps dan oling."
            ))
            return

        self.stdout.write(f"Session path: {session_path}")
        self.stdout.write(f"API ID: {api_id}")

        if options["check"]:
            asyncio.run(self._check(api_id, api_hash, session_path))
        else:
            asyncio.run(self._setup(api_id, api_hash, session_path))

    async def _setup(self, api_id, api_hash, session_path):
        from telethon import TelegramClient

        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            self.stdout.write(self.style.SUCCESS(
                f"Allaqachon avtorizatsiya qilingan: {me.first_name} "
                f"(@{me.username or 'username-yo\'q'}, ID: {me.id})"
            ))
            await client.disconnect()
            return

        phone = input("Telefon raqam (mamlakat kodi bilan, masalan +998901234567): ").strip()
        await client.send_code_request(phone)
        code = input("Telegram dan kelgan OTP kodni kiriting: ").strip()

        try:
            await client.sign_in(phone, code)
        except Exception:
            # 2FA yoqilgan bo'lishi mumkin
            password = input("2FA parol (agar yoqilgan bo'lsa): ").strip()
            await client.sign_in(password=password)

        me = await client.get_me()
        self.stdout.write(self.style.SUCCESS(
            f"\nMuvaffaqiyatli avtorizatsiya: {me.first_name} "
            f"(@{me.username or 'username-yo\'q'}, ID: {me.id})\n"
            f"Session fayl saqlandi: {session_path}.session"
        ))
        await client.disconnect()

    async def _check(self, api_id, api_hash, session_path):
        from telethon import TelegramClient

        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()

        if await client.is_user_authorized():
            me = await client.get_me()
            self.stdout.write(self.style.SUCCESS(
                f"Session haqiqiy. Kirgan foydalanuvchi: {me.first_name} "
                f"(@{me.username or 'username-yo\'q'}, ID: {me.id})"
            ))
        else:
            self.stderr.write(self.style.ERROR(
                "Session avtorizatsiya qilinMAGAN. --check siz ishga tushiring."
            ))

        await client.disconnect()
