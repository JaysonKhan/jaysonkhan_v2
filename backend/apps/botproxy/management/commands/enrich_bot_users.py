"""Enrich bot users with Telegram profile data via Telethon session.

Two-phase approach to resolve Telethon's access_hash requirement:
  Phase 1: Populate entity cache from bot's required channels (iter_participants)
  Phase 2: GetFullUser for cached entities (bio, premium, language, etc.)

For users not found in channels, tries username-based resolution.

Rate limiting:
  - Channel participants: 1 request per 3 seconds (most sensitive operation)
  - GetFullUser: 1 request per 2-3 seconds with jitter
  - FloodWaitError: auto-sleep with exponential backoff
  - Batch pause: 60s every 50 users

Usage:
    python manage.py enrich_bot_users                     # enrich up to 500 users
    python manage.py enrich_bot_users --limit 100         # enrich 100 users
    python manage.py enrich_bot_users --stale-days 7      # re-enrich after 7 days
    python manage.py enrich_bot_users --dry-run            # preview only
    python manage.py enrich_bot_users --user-id 123456    # enrich single user
    python manage.py enrich_bot_users --skip-channels      # skip channel participant fetch
"""
from __future__ import annotations

import json
import logging
import random
import time

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

# Import FloodWaitError at module level for except clauses
try:
    from telethon.errors import FloodWaitError
except ImportError:
    class FloodWaitError(Exception):
        seconds = 0


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
            "--delay", type=float, default=3.0,
            help="So'rovlar orasidagi kutish (sekundda, default: 3.0)",
        )
        parser.add_argument(
            "--batch-pause", type=int, default=60,
            help="Har 50 ta userdan keyin kutish (sekundda, default: 60)",
        )
        parser.add_argument(
            "--skip-channels", action="store_true",
            help="Kanal a'zolarini olishni o'tkazib yuborish (faqat username orqali)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        stale_days = options["stale_days"]
        dry_run = options["dry_run"]
        single_user_id = options["user_id"]
        base_delay = options["delay"]
        batch_pause = options["batch_pause"]
        skip_channels = options["skip_channels"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n═══ Bot Users Enrichment ═══\n"
        ))

        # ── 1. Check Telethon session ────────────────────────────────────────
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

        # ── 2. Get enrichment queue from bot API ────────────────────────────
        from botproxy.client import BotAPIClient, BotAPIError

        bot_client = BotAPIClient()

        if single_user_id:
            user_ids = [single_user_id]
            self.stdout.write(f"  Bitta user: {single_user_id}")
        else:
            self.stdout.write(f"  Enrichment queue so'ralmoqda (limit={limit}, stale={stale_days} kun)...")
            try:
                resp = bot_client._request("GET", f"/api/v1/users/enrichment-queue?limit={limit}&stale_days={stale_days}")
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

        # ── 3. Get Telethon client ───────────────────────────────────────────
        from telegram.telegram_client import get_telegram_client, run_async

        try:
            tg_client = get_telegram_client()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Telethon client xatolik: {e}"))
            return

        user_id_set = set(user_ids)

        # ── 4. Phase 1: Populate entity cache from channels ─────────────────
        #    Telethon needs access_hash to resolve users.
        #    By fetching channel participants, we cache their access_hashes.
        cached_users = {}  # user_id → username (or None)

        if not skip_channels:
            self.stdout.write("\n  📡 Phase 1: Kanal a'zolaridan entity cache to'ldirish...")
            cached_users = self._populate_cache_from_channels(
                tg_client, bot_client, user_id_set
            )
            self.stdout.write(f"  ✅ Kanallardan {len(cached_users)} ta user cached")
        else:
            self.stdout.write("  ⏭ Kanal a'zolari o'tkazib yuborildi (--skip-channels)")

        # Also fetch usernames from bot API for users not in cache
        self.stdout.write("\n  📋 Bot API dan username ro'yxati olinmoqda...")
        usernames_map = self._get_usernames_from_bot_api(bot_client, user_ids)
        # Merge: channel cache takes priority
        for uid, uname in usernames_map.items():
            if uid not in cached_users and uname:
                cached_users[uid] = uname
        self.stdout.write(f"  ✅ Jami {len(cached_users)}/{total} ta user resolve qilish mumkin")

        # ── 5. Phase 2: GetFullUser for each user ───────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n  📊 Phase 2: GetFullUser ({total} ta user)\n"
        ))

        enriched = 0
        errors = 0
        skipped = 0
        flood_waits = 0
        not_resolved = 0
        current_delay = base_delay

        for idx, user_id in enumerate(user_ids, 1):
            # Batch pause every 50 users
            if idx > 1 and (idx - 1) % 50 == 0:
                self.stdout.write(self.style.WARNING(
                    f"\n  ⏸  Batch pause: {batch_pause}s ({idx-1}/{total})\n"
                ))
                time.sleep(batch_pause)

            progress = f"[{idx}/{total}]"

            try:
                # Try to resolve the user
                username = cached_users.get(user_id)
                data = self._fetch_user_data(tg_client, user_id, username)

                if data is None:
                    skipped += 1
                    # Mark as enriched with minimal data so we don't retry immediately
                    try:
                        bot_client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json={
                            "enrichment_source": "telethon_not_found",
                        })
                    except BotAPIError:
                        pass
                    self.stdout.write(f"  {progress} {user_id}: ⏭ topilmadi")
                    time.sleep(current_delay * 0.3)
                    continue

                if data == "NOT_RESOLVED":
                    not_resolved += 1
                    self.stdout.write(f"  {progress} {user_id}: 🔒 resolve imkonsiz (access_hash yo'q)")
                    time.sleep(0.5)
                    continue

                # Send to bot API
                try:
                    bot_client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json=data)
                    enriched += 1

                    # Format status line
                    bio_preview = (data.get("bio") or "")[:30]
                    premium = "⭐" if data.get("is_premium") else ""
                    deleted = "🗑" if data.get("is_deleted") else ""
                    lang = data.get("language_code") or ""
                    usernames_list = json.loads(data.get("usernames_json", "[]"))
                    un_str = ", ".join(f"@{u}" for u in usernames_list[:2]) if usernames_list else ""

                    self.stdout.write(
                        f"  {progress} {user_id}: ✅ {premium}{deleted}"
                        f" lang={lang} {un_str}"
                        f" {bio_preview}"
                    )

                    # Adaptive delay: decrease on success (min 1.5s)
                    current_delay = max(1.5, current_delay * 0.95)

                except BotAPIError as e:
                    self.stdout.write(self.style.WARNING(
                        f"  {progress} {user_id}: ⚠️ API save xatolik: {e}"
                    ))
                    errors += 1

            except FloodWaitError as e:
                flood_waits += 1
                wait = e.seconds + random.randint(5, 15)
                current_delay = min(current_delay * 2, 30)
                self.stdout.write(self.style.ERROR(
                    f"  {progress} {user_id}: 🚫 FloodWait! {e.seconds}s kutish "
                    f"(delay → {current_delay:.1f}s)"
                ))
                time.sleep(wait)
                continue

            except Exception as e:
                errors += 1
                current_delay = min(current_delay * 1.5, 15)
                self.stdout.write(self.style.WARNING(
                    f"  {progress} {user_id}: ❌ {type(e).__name__}: {e}"
                ))

                if errors > 15 and errors > enriched * 2:
                    self.stderr.write(self.style.ERROR(
                        f"\n  🛑 Juda ko'p xatolik ({errors}). To'xtatildi.\n"
                    ))
                    break

            # Random jitter
            jitter = random.uniform(0.3, 1.2)
            time.sleep(current_delay + jitter)

        # ── 6. Summary ──────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n═══ Natija ═══"
        ))
        self.stdout.write(f"  ✅ Boyitildi:          {enriched}/{total}")
        self.stdout.write(f"  ⏭ Topilmadi:          {skipped}")
        self.stdout.write(f"  🔒 Resolve imkonsiz:  {not_resolved}")
        self.stdout.write(f"  ❌ Xatoliklar:         {errors}")
        self.stdout.write(f"  🚫 FloodWait:         {flood_waits}")
        self.stdout.write("")

    def _populate_cache_from_channels(
        self, tg_client, bot_client, target_user_ids: set[int]
    ) -> dict[int, str | None]:
        """Fetch participants from bot's required channels to populate Telethon entity cache.

        This is the key step — Telethon needs to "see" users before GetFullUser works.
        Channel participants iteration caches access_hashes automatically.

        Returns: {user_id: username_or_None} for users found in channels.
        """
        from botproxy.client import BotAPIError
        from telegram.telegram_client import run_async

        cached = {}

        # Get required channels from bot API
        try:
            resp = bot_client._request("GET", "/api/v1/channels")
            channels = resp.json().get("channels", [])
        except BotAPIError:
            self.stdout.write(self.style.WARNING("  ⚠️ Kanallar ro'yxati olinmadi"))
            return cached

        if not channels:
            self.stdout.write("  ⚠️ Majburiy kanallar yo'q")
            return cached

        for ch in channels:
            ch_username = ch.get("channel_username", "")
            if not ch_username:
                continue

            clean_username = ch_username.lstrip("@")
            self.stdout.write(f"  📡 @{clean_username} a'zolari olinmoqda...")

            try:
                async def _iter_participants(username=clean_username):
                    found = {}
                    try:
                        entity = await tg_client.get_entity(username)
                        count = 0
                        async for user in tg_client.iter_participants(entity, limit=10000):
                            count += 1
                            if user.id in target_user_ids:
                                found[user.id] = user.username
                            # Brief yield every 200 users to avoid blocking
                            if count % 200 == 0:
                                import asyncio
                                await asyncio.sleep(0.1)
                        return found, count
                    except Exception as e:
                        err_str = str(e).lower()
                        if "chat_admin_required" in err_str:
                            return found, -1  # Not admin
                        raise

                found, total_in_ch = run_async(_iter_participants())

                if total_in_ch == -1:
                    self.stdout.write(f"    ⚠️ @{clean_username}: admin huquqi kerak")
                else:
                    cached.update(found)
                    self.stdout.write(
                        f"    ✅ @{clean_username}: {total_in_ch} a'zo, "
                        f"{len(found)} ta target user topildi"
                    )

                # Pause between channels to avoid FloodWait
                time.sleep(5)

            except FloodWaitError as e:
                self.stdout.write(self.style.ERROR(
                    f"    🚫 @{clean_username}: FloodWait {e.seconds}s!"
                ))
                time.sleep(e.seconds + 10)
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"    ❌ @{clean_username}: {type(e).__name__}: {e}"
                ))
                time.sleep(3)

        return cached

    def _get_usernames_from_bot_api(
        self, bot_client, user_ids: list[int]
    ) -> dict[int, str | None]:
        """Fetch usernames for users from bot API (stored during bot interactions)."""
        from botproxy.client import BotAPIError

        result = {}
        # Get users in pages
        page = 1
        per_page = 100
        try:
            while True:
                resp = bot_client._request(
                    "GET", f"/api/v1/users?page={page}&per_page={per_page}"
                )
                data = resp.json()
                users = data.get("users", [])
                if not users:
                    break
                for u in users:
                    uid = u.get("user_id")
                    uname = u.get("username")
                    if uid in set(user_ids) and uname:
                        result[uid] = uname
                page += 1
                total_pages = max(1, -(-data.get("total", 0) // per_page))
                if page > total_pages:
                    break
        except BotAPIError as e:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Username olishda xatolik: {e}"))

        return result

    def _fetch_user_data(self, client, user_id: int, username: str | None = None) -> dict | str | None:
        """Fetch full user data via Telethon GetFullUserRequest.

        Resolution strategy:
        1. If username available → resolve via @username
        2. If in entity cache (from channel) → use InputPeerUser
        3. Try InputPeerUser(id, access_hash=0) as last resort

        Returns:
            dict: enrichment data
            None: user not found / deleted
            "NOT_RESOLVED": cannot resolve user (no access_hash)
        """
        from telegram.telegram_client import run_async

        async def _get_full_user():
            from telethon.tl.functions.users import GetFullUserRequest
            from telethon.tl.types import (
                InputPeerUser,
                UserStatusOnline,
                UserStatusOffline,
                UserStatusRecently,
                UserStatusLastWeek,
                UserStatusLastMonth,
            )

            # Step 1: Resolve entity
            entity = None
            resolve_method = "unknown"

            # Try username first (most reliable)
            if username:
                try:
                    entity = await client.get_input_entity(f"@{username}")
                    resolve_method = "username"
                except Exception:
                    pass

            # Try from internal cache (populated by iter_participants)
            if entity is None:
                try:
                    entity = await client.get_input_entity(user_id)
                    resolve_method = "cache"
                except Exception:
                    pass

            # Try InputPeerUser with access_hash=0 (works if user has interacted with session account)
            if entity is None:
                try:
                    entity = InputPeerUser(user_id, access_hash=0)
                    # Test if it actually works
                    await client(GetFullUserRequest(entity))
                    resolve_method = "zero_hash"
                except Exception as e:
                    err_str = str(e).lower()
                    if "could not find" in err_str or "input entity" in err_str:
                        return "NOT_RESOLVED"
                    if "user_id_invalid" in err_str or "peer_id_invalid" in err_str:
                        return None
                    raise

            # Step 2: GetFullUser
            try:
                if resolve_method != "zero_hash":  # Already fetched for zero_hash test
                    full_result = await client(GetFullUserRequest(entity))
                else:
                    full_result = await client(GetFullUserRequest(entity))
            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in (
                    "user_id_invalid", "peer_id_invalid", "input_user_deactivated"
                )):
                    return None
                raise

            full_user = full_result.full_user
            user_obj = None
            for u in full_result.users:
                if u.id == user_id:
                    user_obj = u
                    break

            if not user_obj:
                return None

            # Step 3: Extract data
            data = {
                "enrichment_source": f"telethon:{resolve_method}",
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

            # DC ID (from photo)
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

            # Updated name/username
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
            if hasattr(user_obj, "usernames") and user_obj.usernames:
                for un in user_obj.usernames:
                    uname = getattr(un, "username", None)
                    if uname and uname not in usernames:
                        usernames.append(uname)
            if usernames:
                data["usernames_json"] = json.dumps(usernames)

            # Phone — only if in contacts
            if getattr(user_obj, "phone", None):
                phone = user_obj.phone
                if not phone.startswith("+"):
                    phone = f"+{phone}"
                data["phone2"] = phone

            return data

        return run_async(_get_full_user())
