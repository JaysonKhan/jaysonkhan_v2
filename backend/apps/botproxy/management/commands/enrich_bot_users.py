"""Enrich bot users with Telegram profile data via Telethon session.

Uses the configured Telegram session (MTProto) to fetch extended user info
(bio, premium status, language, last online, etc.) for each bot user,
then sends enriched data back to the bot API.

Rate limiting:
  - 1 GetFullUser request per 2-3 seconds (safe for Telegram)
  - FloodWaitError auto-sleep with exponential backoff
  - Max 500 users per run (configurable)
  - Adaptive delay: increases on errors, decreases on success

Usage:
    python manage.py enrich_bot_users                     # enrich up to 500 users
    python manage.py enrich_bot_users --limit 100         # enrich 100 users
    python manage.py enrich_bot_users --stale-days 7      # re-enrich after 7 days
    python manage.py enrich_bot_users --dry-run            # preview only
    python manage.py enrich_bot_users --user-id 123456    # enrich single user
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bot foydalanuvchilarini Telethon sessiya orqali boyitish (bio, premium, til, va h.k.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=500,
            help="Maksimum foydalanuvchilar soni (default: 500)",
        )
        parser.add_argument(
            "--stale-days", type=int, default=30,
            help="Necha kundan keyin qayta boyitish (default: 30)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Faqat qancha user bor ko'rsatish, hech narsa o'zgartirmaslik",
        )
        parser.add_argument(
            "--user-id", type=int, default=None,
            help="Faqat bitta user ID ni boyitish",
        )
        parser.add_argument(
            "--delay", type=float, default=2.5,
            help="So'rovlar orasidagi kutish (sekundda, default: 2.5)",
        )
        parser.add_argument(
            "--batch-pause", type=int, default=60,
            help="Har 50 ta userdan keyin kutish (sekundda, default: 60)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        stale_days = options["stale_days"]
        dry_run = options["dry_run"]
        single_user_id = options["user_id"]
        base_delay = options["delay"]
        batch_pause = options["batch_pause"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n═══ Bot Users Enrichment ═══\n"
        ))

        # 1. Check Telethon session
        self.stdout.write("  Telegram sessiya tekshirilmoqda...")
        try:
            from telegram.telegram_client import check_session_status
            status = check_session_status()
            if not status.get("authorized"):
                self.stderr.write(self.style.ERROR(
                    "❌ Telegram sessiya avtorizatsiya qilinmagan!\n"
                    "   Admin panel → Telegram Session sahifasidan sessiya yarating."
                ))
                return
            user = status.get("user", {})
            self.stdout.write(self.style.SUCCESS(
                f"  ✅ Sessiya: {user.get('first_name', '')} @{user.get('username', '')} (ID: {user.get('id', '')})"
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Sessiya xatolik: {e}"))
            return

        # 2. Get enrichment queue from bot API
        from botproxy.client import BotAPIClient, BotAPIError

        client = BotAPIClient()

        if single_user_id:
            user_ids = [single_user_id]
            self.stdout.write(f"  Bitta user: {single_user_id}")
        else:
            self.stdout.write(f"  Enrichment queue so'ralmoqda (limit={limit}, stale={stale_days} kun)...")
            try:
                resp = client._request("GET", f"/api/v1/users/enrichment-queue?limit={limit}&stale_days={stale_days}")
                data = resp.json()
                user_ids = data.get("user_ids", [])
            except BotAPIError as e:
                self.stderr.write(self.style.ERROR(f"❌ Bot API xatolik: {e}"))
                return

        total = len(user_ids)
        if total == 0:
            self.stdout.write(self.style.SUCCESS("  ✅ Barcha userlar allaqachon boyitilgan!"))
            return

        self.stdout.write(f"  📋 {total} ta user boyitish kerak")

        if dry_run:
            self.stdout.write(self.style.WARNING("  --dry-run: Hech narsa o'zgartirilmaydi"))
            for uid in user_ids[:20]:
                self.stdout.write(f"    • {uid}")
            if total > 20:
                self.stdout.write(f"    ... va {total - 20} ta boshqa")
            return

        # 3. Process users
        from telegram.telegram_client import get_telegram_client, run_async

        try:
            tg_client = get_telegram_client()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Telethon client xatolik: {e}"))
            return

        enriched = 0
        errors = 0
        skipped = 0
        flood_waits = 0
        current_delay = base_delay

        self.stdout.write(f"\n  Boshlash... (delay={base_delay}s, batch_pause={batch_pause}s)\n")

        for idx, user_id in enumerate(user_ids, 1):
            # Batch pause every 50 users
            if idx > 1 and (idx - 1) % 50 == 0:
                self.stdout.write(self.style.WARNING(
                    f"\n  ⏸  Batch pause: {batch_pause}s kutish ({idx-1}/{total} bajarildi)\n"
                ))
                time.sleep(batch_pause)

            progress = f"[{idx}/{total}]"

            try:
                data = self._fetch_user_data(tg_client, user_id)

                if data is None:
                    self.stdout.write(f"  {progress} {user_id}: ⏭ topilmadi/private")
                    skipped += 1
                    time.sleep(current_delay * 0.5)  # Shorter delay for skips
                    continue

                # Send to bot API
                try:
                    client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json=data)
                    enriched += 1

                    # Format status line
                    bio_preview = (data.get("bio") or "")[:30]
                    premium = "⭐" if data.get("is_premium") else ""
                    deleted = "🗑" if data.get("is_deleted") else ""
                    lang = data.get("language_code") or ""
                    usernames = json.loads(data.get("usernames_json", "[]"))
                    un_str = ", ".join(f"@{u}" for u in usernames[:2]) if usernames else ""

                    self.stdout.write(
                        f"  {progress} {user_id}: ✅ {premium}{deleted}"
                        f" lang={lang} {un_str}"
                        f" {bio_preview}"
                    )

                    # Adaptive delay: decrease slightly on success (min 1.5s)
                    current_delay = max(1.5, current_delay * 0.95)

                except BotAPIError as e:
                    self.stdout.write(self.style.WARNING(
                        f"  {progress} {user_id}: ⚠️ API save xatolik: {e}"
                    ))
                    errors += 1

            except FloodWaitError as e:
                flood_waits += 1
                wait = e.seconds + random.randint(5, 15)  # Extra jitter
                current_delay = min(current_delay * 2, 30)  # Double delay, max 30s
                self.stdout.write(self.style.ERROR(
                    f"  {progress} {user_id}: 🚫 FloodWait! {e.seconds}s + jitter = {wait}s kutish "
                    f"(delay → {current_delay:.1f}s)"
                ))
                time.sleep(wait)
                continue

            except Exception as e:
                errors += 1
                current_delay = min(current_delay * 1.5, 15)  # Increase delay on errors
                self.stdout.write(self.style.WARNING(
                    f"  {progress} {user_id}: ❌ {type(e).__name__}: {e}"
                ))

                # If too many errors in a row, abort
                if errors > 10 and errors > enriched:
                    self.stderr.write(self.style.ERROR(
                        f"\n  🛑 Juda ko'p xatolik ({errors}). To'xtatildi.\n"
                    ))
                    break

            # Random jitter to look more natural
            jitter = random.uniform(0.5, 1.5)
            time.sleep(current_delay + jitter)

        # 4. Summary
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n═══ Natija ═══"
        ))
        self.stdout.write(f"  ✅ Boyitildi:     {enriched}/{total}")
        self.stdout.write(f"  ⏭ O'tkazib yubordi: {skipped}")
        self.stdout.write(f"  ❌ Xatoliklar:    {errors}")
        self.stdout.write(f"  🚫 FloodWait:    {flood_waits}")
        self.stdout.write("")

    def _fetch_user_data(self, client, user_id: int) -> dict | None:
        """Fetch full user data via Telethon GetFullUserRequest.

        Returns dict of enrichment fields, or None if user is inaccessible.
        """
        from telegram.telegram_client import run_async

        async def _get_full_user():
            from telethon.tl.functions.users import GetFullUserRequest
            from telethon.tl.types import (
                User,
                UserStatusOnline,
                UserStatusOffline,
                UserStatusRecently,
                UserStatusLastWeek,
                UserStatusLastMonth,
            )

            try:
                full_result = await client(GetFullUserRequest(user_id))
            except Exception as e:
                err_str = str(e).lower()
                # User doesn't exist or is private
                if any(x in err_str for x in ("user_id_invalid", "user not found", "peer_id_invalid")):
                    return None
                raise

            full_user = full_result.full_user
            # The User object is in full_result.users list
            user_obj = None
            for u in full_result.users:
                if u.id == user_id:
                    user_obj = u
                    break

            if not user_obj:
                return None

            # Extract data
            data = {
                "enrichment_source": "telethon",
            }

            # Bio
            if full_user.about:
                data["bio"] = full_user.about

            # Premium status
            data["is_premium"] = 1 if getattr(user_obj, "premium", False) else 0

            # Deleted account
            data["is_deleted"] = 1 if getattr(user_obj, "deleted", False) else 0

            # Bot flag
            data["is_bot"] = 1 if getattr(user_obj, "bot", False) else 0

            # Language code
            if getattr(user_obj, "lang_code", None):
                data["language_code"] = user_obj.lang_code

            # DC ID (from photo if available)
            if getattr(user_obj, "photo", None) and hasattr(user_obj.photo, "dc_id"):
                data["dc_id"] = user_obj.photo.dc_id

            # Common chats count
            if hasattr(full_user, "common_chats_count"):
                data["common_chats_count"] = full_user.common_chats_count

            # Last online status
            status = getattr(user_obj, "status", None)
            if isinstance(status, UserStatusOnline):
                data["last_online_at"] = status.expires.isoformat() if status.expires else None
            elif isinstance(status, UserStatusOffline):
                data["last_online_at"] = status.was_online.isoformat() if status.was_online else None
            elif isinstance(status, UserStatusRecently):
                data["last_online_at"] = "recently"
            elif isinstance(status, UserStatusLastWeek):
                data["last_online_at"] = "last_week"
            elif isinstance(status, UserStatusLastMonth):
                data["last_online_at"] = "last_month"

            # Updated name/username (may have changed since bot interaction)
            if user_obj.first_name:
                data["first_name"] = user_obj.first_name
            if user_obj.last_name:
                data["last_name"] = user_obj.last_name
            if user_obj.username:
                data["username"] = user_obj.username

            # Multiple usernames (basic + collectible)
            usernames = []
            if user_obj.username:
                usernames.append(user_obj.username)
            # Collectible usernames (Telegram Premium feature)
            if hasattr(user_obj, "usernames") and user_obj.usernames:
                for un in user_obj.usernames:
                    uname = getattr(un, "username", None)
                    if uname and uname not in usernames:
                        usernames.append(uname)
            if usernames:
                data["usernames_json"] = json.dumps(usernames)

            # Phone number — only available if user is in our contacts
            if getattr(user_obj, "phone", None):
                # Check if it's different from primary phone
                data["phone2"] = f"+{user_obj.phone}" if not user_obj.phone.startswith("+") else user_obj.phone

            return data

        return run_async(_get_full_user())


# Import at module level for except clause
try:
    from telethon.errors import FloodWaitError
except ImportError:
    class FloodWaitError(Exception):
        seconds = 0
