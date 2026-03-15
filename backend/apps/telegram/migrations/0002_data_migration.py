"""Data migration: copy existing data into the unified TelegramEntity model.

1. TelegramProfile → TelegramEntity (preserving PKs so FK values remain valid)
2. OsintPhotoCache → TelegramEntity photo fields (merge by telegram_id)
3. TelegramSession → telegram.TelegramSession (copy from botproxy)
4. Create EntitySource records for migrated profiles (service='site')
"""
from django.db import migrations


def forward(apps, schema_editor):
    # ── 1. TelegramProfile → TelegramEntity ──────────────────────────────────
    TelegramProfile = apps.get_model("interactions", "TelegramProfile")
    TelegramEntity = apps.get_model("telegram", "TelegramEntity")
    EntitySource = apps.get_model("telegram", "EntitySource")

    for tp in TelegramProfile.objects.all():
        TelegramEntity.objects.create(
            id=tp.id,  # Preserve PK so existing FKs remain valid
            telegram_id=tp.telegram_id,
            entity_type="user",
            first_name=tp.first_name or "",
            last_name=tp.last_name or "",
            username=tp.username or "",
            photo_url=tp.photo_url or "",
            auth_date=tp.auth_date,
        )
        EntitySource.objects.create(
            entity_id=tp.id,
            service="site",
        )

    # ── 2. OsintPhotoCache → TelegramEntity photo fields ─────────────────────
    OsintPhotoCache = apps.get_model("botproxy", "OsintPhotoCache")
    for pc in OsintPhotoCache.objects.all():
        try:
            tg_id = int(pc.entity_id)
        except (ValueError, TypeError):
            continue  # Skip non-numeric entity IDs

        entity, created = TelegramEntity.objects.get_or_create(
            telegram_id=tg_id,
            defaults={"entity_type": "user"},
        )
        entity.photo_file = pc.photo_path or ""
        entity.photo_fetched_at = pc.fetched_at
        entity.has_photo = pc.has_photo
        entity.save(update_fields=["photo_file", "photo_fetched_at", "has_photo"])

        # Mark as OSINT source if not already a site user
        EntitySource.objects.get_or_create(
            entity=entity,
            service="osint",
        )

    # ── 3. TelegramSession → telegram.TelegramSession ─────────────────────────
    OldSession = apps.get_model("botproxy", "TelegramSession")
    NewSession = apps.get_model("telegram", "TelegramSession")
    for s in OldSession.objects.all():
        NewSession.objects.create(
            session_string=s.session_string,
            account_id=s.account_id,
            account_name=s.account_name or "",
        )


def backward(apps, schema_editor):
    """Reverse: clear telegram tables (original data remains in botproxy/interactions)."""
    TelegramEntity = apps.get_model("telegram", "TelegramEntity")
    EntitySource = apps.get_model("telegram", "EntitySource")
    NewSession = apps.get_model("telegram", "TelegramSession")

    EntitySource.objects.all().delete()
    TelegramEntity.objects.all().delete()
    NewSession.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("telegram", "0001_initial"),
        ("interactions", "0005_alter_adminlogmessage_message_id"),
        ("botproxy", "0004_telegramsession"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
