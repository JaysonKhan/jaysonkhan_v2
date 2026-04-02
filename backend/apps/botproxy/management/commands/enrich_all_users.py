"""Full enrichment runner — processes ALL bot users in batches.

Designed to run on server via screen/tmux for hours.
Splits work into batches, logs progress, calculates ETA.

Expected time for 70,000 users:
  - ~53,000 with username: ~4.5s each = ~66 hours
  - ~17,000 without username: ~0.5s each = ~2.5 hours
  - Total: ~68 hours (with batch pauses ~72 hours = 3 days)

Usage:
    # On server (jaysonkhan):
    screen -S enrich
    cd /var/www/jaysonkhan/backend
    source venv/bin/activate
    python manage.py enrich_all_users
    # Ctrl+A, D to detach
    # screen -r enrich to reattach

    # Or with nohup:
    nohup python manage.py enrich_all_users > /var/log/enrich_users.log 2>&1 &
"""
from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

try:
    from telethon.errors import FloodWaitError
except ImportError:
    class FloodWaitError(Exception):
        seconds = 0


BATCH_SIZE = 500  # users per batch
INTER_BATCH_PAUSE = 120  # seconds between batches
STALE_DAYS = 30


class Command(BaseCommand):
    help = "Barcha bot foydalanuvchilarini Telethon orqali boyitish (uzun jarayon — screen/tmux da ishga tushiring)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delay", type=float, default=3.5,
            help="So'rovlar orasidagi kutish (default: 3.5s)",
        )
        parser.add_argument(
            "--resume", action="store_true",
            help="Oldingi jarayonni davom ettirish (enriched_at bor userlarni o'tkazib yuboradi)",
        )
        parser.add_argument(
            "--stale-days", type=int, default=STALE_DAYS,
            help=f"Qayta boyitish kunlari (default: {STALE_DAYS})",
        )

    def handle(self, *args, **options):
        base_delay = options["delay"]
        stale_days = options["stale_days"]
        start_time = time.monotonic()
        started_at = datetime.now()

        self._log("=" * 60)
        self._log(f"ENRICHMENT BOSHLANDI: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log("=" * 60)

        # 1. Check session
        try:
            from telegram.telegram_client import check_session_status
            status = check_session_status()
            if not status.get("authorized"):
                self._error("Telegram sessiya avtorizatsiya qilinmagan!")
                return
            user = status.get("user", {})
            self._log(f"Sessiya: {user.get('first_name', '')} @{user.get('username', '')} (ID: {user.get('id', '')})")
        except Exception as e:
            self._error(f"Sessiya xatolik: {e}")
            return

        # 2. Get client
        from botproxy.client import BotAPIClient, BotAPIError
        from telegram.telegram_client import get_telegram_client, run_async

        bot_client = BotAPIClient()
        try:
            tg_client = get_telegram_client()
        except Exception as e:
            self._error(f"Telethon client xatolik: {e}")
            return

        # 3. Get total count
        try:
            resp = bot_client._request("GET", "/api/v1/users/count")
            total_users = resp.json().get("count", 0)
        except BotAPIError:
            total_users = 70000  # fallback estimate

        self._log(f"Jami foydalanuvchilar: {total_users}")

        # Calculate ETA (rough estimate: 60% resolvable at 4.5s, 40% skip at 0.5s)
        resolvable = int(total_users * 0.6)
        non_resolvable = total_users - resolvable
        est_seconds = (resolvable * 4.5) + (non_resolvable * 0.5) + ((total_users // 500) * INTER_BATCH_PAUSE)
        est_hours = est_seconds / 3600
        eta = started_at + timedelta(seconds=est_seconds)
        self._log(f"Taxminiy vaqt: {est_hours:.1f} soat")
        self._log(f"Taxminiy tugash: {eta.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log("")

        # 4. Get all usernames in one shot
        self._log("Bot API dan barcha username lar olinmoqda...")
        usernames_map = self._get_all_usernames(bot_client)
        self._log(f"Username topildi: {len(usernames_map)}/{total_users}")

        # 5. Process in batches
        grand_enriched = 0
        grand_not_resolved = 0
        grand_skipped = 0
        grand_errors = 0
        grand_flood = 0
        batch_num = 0

        while True:
            batch_num += 1

            # Get next batch from queue
            try:
                resp = bot_client._request(
                    "GET",
                    f"/api/v1/users/enrichment-queue?limit={BATCH_SIZE}&stale_days={stale_days}"
                )
                user_ids = resp.json().get("user_ids", [])
            except BotAPIError as e:
                self._error(f"Queue olishda xatolik: {e}")
                time.sleep(30)
                continue

            if not user_ids:
                self._log("✅ BARCHA USERLAR BOYITILDI!")
                break

            self._log(f"\n{'─' * 50}")
            self._log(f"BATCH #{batch_num}: {len(user_ids)} ta user")
            self._log(f"Progress: {grand_enriched + grand_not_resolved + grand_skipped}/{total_users}")
            elapsed = time.monotonic() - start_time
            if grand_enriched + grand_not_resolved + grand_skipped > 0:
                rate = elapsed / (grand_enriched + grand_not_resolved + grand_skipped)
                remaining = (total_users - grand_enriched - grand_not_resolved - grand_skipped) * rate
                eta_str = (datetime.now() + timedelta(seconds=remaining)).strftime('%Y-%m-%d %H:%M')
                self._log(f"ETA: {eta_str} ({remaining/3600:.1f} soat qoldi)")
            self._log(f"{'─' * 50}")

            enriched, not_resolved, skipped, errors, flood = self._process_batch(
                tg_client, bot_client, user_ids, usernames_map, base_delay
            )

            grand_enriched += enriched
            grand_not_resolved += not_resolved
            grand_skipped += skipped
            grand_errors += errors
            grand_flood += flood

            self._log(f"  Batch #{batch_num}: +{enriched} boyitildi, "
                       f"+{not_resolved} resolve imkonsiz, +{skipped} skip, +{errors} xato")

            # Inter-batch pause
            if user_ids:
                self._log(f"  ⏸ {INTER_BATCH_PAUSE}s batch orasidagi kutish...")
                time.sleep(INTER_BATCH_PAUSE)

        # 6. Final summary
        total_time = time.monotonic() - start_time
        finished_at = datetime.now()

        self._log("")
        self._log("=" * 60)
        self._log(f"ENRICHMENT TUGADI: {finished_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Umumiy vaqt: {total_time/3600:.1f} soat ({total_time/60:.0f} daqiqa)")
        self._log(f"✅ Boyitildi:          {grand_enriched}")
        self._log(f"🔒 Resolve imkonsiz:  {grand_not_resolved}")
        self._log(f"⏭ Topilmadi:          {grand_skipped}")
        self._log(f"❌ Xatoliklar:         {grand_errors}")
        self._log(f"🚫 FloodWait:         {grand_flood}")
        self._log(f"Batchlar:             {batch_num}")
        self._log("=" * 60)

    def _process_batch(self, tg_client, bot_client, user_ids, usernames_map, base_delay):
        """Process a single batch of users."""
        from botproxy.client import BotAPIError

        enriched = 0
        not_resolved = 0
        skipped = 0
        errors = 0
        flood_waits = 0
        current_delay = base_delay
        total = len(user_ids)

        for idx, user_id in enumerate(user_ids, 1):
            # Micro-batch pause every 50
            if idx > 1 and (idx - 1) % 50 == 0:
                self._log(f"    ⏸ 60s micro-pause ({idx-1}/{total})")
                time.sleep(60)

            try:
                username = usernames_map.get(user_id)
                data = self._fetch_user_data(tg_client, user_id, username)

                if data is None:
                    skipped += 1
                    try:
                        bot_client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json={
                            "enrichment_source": "telethon_not_found",
                        })
                    except BotAPIError:
                        pass
                    time.sleep(0.3)
                    continue

                if data == "NOT_RESOLVED":
                    not_resolved += 1
                    try:
                        bot_client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json={
                            "enrichment_source": "no_access_hash",
                        })
                    except BotAPIError:
                        pass
                    time.sleep(0.2)
                    continue

                # Save to bot API
                saved = False
                for attempt in range(3):
                    try:
                        bot_client._request("PATCH", f"/api/v1/users/{user_id}/enrich", json=data)
                        saved = True
                        break
                    except BotAPIError as e:
                        if e.status == 429 and attempt < 2:
                            time.sleep(5 * (attempt + 1))
                            continue
                        raise

                if saved:
                    enriched += 1
                    if enriched % 25 == 0 or enriched <= 3:
                        bio = (data.get("bio") or "")[:25]
                        premium = "⭐" if data.get("is_premium") else ""
                        self._log(f"    [{idx}/{total}] {user_id}: ✅{premium} {bio}")
                    current_delay = max(1.5, current_delay * 0.97)

            except FloodWaitError as e:
                flood_waits += 1
                wait = e.seconds + random.randint(10, 30)
                current_delay = min(current_delay * 2, 30)
                self._log(f"    [{idx}/{total}] 🚫 FloodWait {e.seconds}s! Kutish: {wait}s")
                time.sleep(wait)
                continue

            except Exception as e:
                errors += 1
                current_delay = min(current_delay * 1.3, 15)
                if errors % 10 == 0:
                    self._log(f"    [{idx}/{total}] ❌ {type(e).__name__}: {str(e)[:60]}")
                if errors > 30 and errors > enriched * 3:
                    self._log(f"    🛑 Juda ko'p xatolik! Batch to'xtatildi.")
                    break

            jitter = random.uniform(0.2, 1.0)
            time.sleep(current_delay + jitter)

        return enriched, not_resolved, skipped, errors, flood_waits

    def _get_all_usernames(self, bot_client):
        """Fetch ALL usernames from bot API paginated."""
        from botproxy.client import BotAPIError
        result = {}
        page = 1
        per_page = 100
        while True:
            try:
                resp = bot_client._request("GET", f"/api/v1/users?page={page}&per_page={per_page}")
                data = resp.json()
                users = data.get("users", [])
                if not users:
                    break
                for u in users:
                    uid = u.get("user_id")
                    uname = u.get("username")
                    if uid and uname:
                        result[uid] = uname
                total_pages = max(1, -(-data.get("total", 0) // per_page))
                if page >= total_pages:
                    break
                page += 1
                if page % 50 == 0:
                    time.sleep(1)  # Don't flood bot API
            except BotAPIError as e:
                self._log(f"  ⚠️ Username page {page} xatolik: {e}")
                time.sleep(5)
                if page > 1:
                    page += 1  # Try to skip problematic page
                else:
                    break
        return result

    def _fetch_user_data(self, client, user_id, username=None):
        """Same as enrich_bot_users._fetch_user_data but imported inline."""
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

            entity = None
            resolve_method = "unknown"

            if username:
                try:
                    entity = await client.get_input_entity(f"@{username}")
                    resolve_method = "username"
                except Exception:
                    pass

            if entity is None:
                try:
                    entity = await client.get_input_entity(user_id)
                    resolve_method = "cache"
                except Exception:
                    pass

            if entity is None:
                try:
                    entity = InputPeerUser(user_id, access_hash=0)
                    await client(GetFullUserRequest(entity))
                    resolve_method = "zero_hash"
                except Exception as e:
                    err_str = str(e).lower()
                    err_type = type(e).__name__.lower()
                    if any(x in err_str or x in err_type for x in (
                        "could not find", "input entity", "user_id_invalid",
                        "peer_id_invalid", "useridinvalid",
                    )):
                        return "NOT_RESOLVED"
                    raise

            try:
                full_result = await client(GetFullUserRequest(entity))
            except Exception as e:
                err_str = str(e).lower()
                err_type = type(e).__name__.lower()
                if any(x in err_str or x in err_type for x in (
                    "user_id_invalid", "peer_id_invalid", "input_user_deactivated",
                    "useridinvalid",
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

            data = {"enrichment_source": f"telethon:{resolve_method}"}

            if full_user.about:
                data["bio"] = full_user.about
            data["is_premium"] = 1 if getattr(user_obj, "premium", False) else 0
            data["is_deleted"] = 1 if getattr(user_obj, "deleted", False) else 0
            data["is_bot"] = 1 if getattr(user_obj, "bot", False) else 0
            if getattr(user_obj, "lang_code", None):
                data["language_code"] = user_obj.lang_code
            if getattr(user_obj, "photo", None) and hasattr(user_obj.photo, "dc_id"):
                data["dc_id"] = user_obj.photo.dc_id
            if hasattr(full_user, "common_chats_count"):
                data["common_chats_count"] = full_user.common_chats_count

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

            if user_obj.first_name:
                data["first_name"] = user_obj.first_name
            if user_obj.last_name:
                data["last_name"] = user_obj.last_name
            if user_obj.username:
                data["username"] = user_obj.username

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

            if getattr(user_obj, "phone", None):
                phone = user_obj.phone
                if not phone.startswith("+"):
                    phone = f"+{phone}"
                data["phone2"] = phone

            return data

        return run_async(_get_full_user())

    def _log(self, msg):
        self.stdout.write(msg)
        self.stdout.flush()

    def _error(self, msg):
        self.stderr.write(self.style.ERROR(msg))
