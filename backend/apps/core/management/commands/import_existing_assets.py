"""Scan MEDIA_ROOT + model FileFields and register every existing image as an Asset.

Idempotent: if an Asset with the same source_path already exists, we update its
usage_summary instead of creating a duplicate.

Usage:
    python manage.py import_existing_assets [--dry-run] [--scan-fs] [--purge-orphans]

Options:
    --dry-run         Show what would be created without writing.
    --scan-fs         Also walk MEDIA_ROOT for files not referenced by any model.
    --purge-orphans   Delete Asset rows whose file no longer exists on disk.
"""
import os
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import FileField, ImageField


# Folder mapping: top-level path prefix → Asset folder
FOLDER_MAP = {
    'projects': 'apps',
    'project': 'apps',
    'apps': 'apps',
    'team': 'team',
    'staff_photos': 'team',
    'profile_pics': 'team',
    'blog': 'journal',
    'posts': 'journal',
    'journal': 'journal',
    'comments': 'journal',
    'uploads': 'journal',
    'hero': 'hero',
    'about': 'brand',
    'og': 'brand',
    'favicon': 'brand',
    'logo': 'brand',
    'brand': 'brand',
    'branding': 'brand',
    'seo': 'brand',
    'cv': 'brand',
    'experience': 'experience',
    'product': 'product',
    'uni_logos': 'product',
    'osint': 'misc',
    'assets': 'misc',
}

# File extensions worth importing (skip text/docs/db backups)
IMG_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'}
MEDIA_EXTS = IMG_EXTS | {'.mp4', '.mov', '.webm', '.pdf'}


class Command(BaseCommand):
    help = "Register every existing image/asset on disk as an Asset model row."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Don't write to DB.")
        parser.add_argument('--scan-fs', action='store_true', help="Also walk MEDIA_ROOT for unreferenced files.")
        parser.add_argument('--purge-orphans', action='store_true', help="Delete Asset rows whose files no longer exist.")

    def handle(self, *args, **opts):
        from core.models import Asset

        self.dry = opts['dry_run']
        self.created = 0
        self.updated = 0
        self.skipped = 0
        self.purged = 0

        if self.dry:
            self.stdout.write(self.style.WARNING("DRY RUN — no DB writes"))

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write(self.style.ERROR(f"MEDIA_ROOT does not exist: {media_root}"))
            return

        # ── 1. Scan model FileFields ─────────────────────────────────────
        usage_index = {}  # source_path → list of "Model: identifier · field" strings

        for model in apps.get_models():
            for field in model._meta.get_fields():
                if not isinstance(field, (FileField, ImageField)):
                    continue
                # Skip the Asset model itself
                if model is Asset:
                    continue

                qs = model.objects.exclude(**{f"{field.name}": ''}).exclude(**{f"{field.name}__isnull": True})
                for obj in qs.iterator():
                    fobj = getattr(obj, field.name, None)
                    if not fobj or not fobj.name:
                        continue
                    source_path = fobj.name
                    full = media_root / source_path
                    if not full.is_file():
                        continue
                    label = self._object_label(obj, model, field.name)
                    usage_index.setdefault(source_path, []).append(label)

        # ── 2. Optionally scan filesystem for unreferenced files ─────────
        if opts['scan_fs']:
            for root, _, files in os.walk(media_root):
                rel_root = Path(root).relative_to(media_root)
                for fname in files:
                    p = (rel_root / fname).as_posix()
                    if p.startswith('.'):
                        continue
                    ext = Path(fname).suffix.lower()
                    if ext not in MEDIA_EXTS:
                        continue
                    if p not in usage_index:
                        usage_index.setdefault(p, [])  # unreferenced

        # ── 3. Create / update Asset rows ────────────────────────────────
        for source_path, usages in usage_index.items():
            self._import_one(source_path, usages, media_root)

        # ── 4. Purge orphans ─────────────────────────────────────────────
        if opts['purge_orphans']:
            for asset in Asset.objects.all().iterator():
                full = media_root / asset.file.name if asset.file and asset.file.name else None
                if full is None or not full.is_file():
                    self.stdout.write(self.style.WARNING(f"  ✗ orphan: {asset.file.name} (id={asset.pk})"))
                    if not self.dry:
                        asset.delete()
                    self.purged += 1

        # ── 5. Report ─────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✓ Done. created={self.created} updated={self.updated} skipped={self.skipped} purged={self.purged}"
        ))

    def _import_one(self, source_path, usages, media_root):
        from core.models import Asset

        # Detect folder from path prefix
        prefix = source_path.split('/', 1)[0].lower()
        folder = FOLDER_MAP.get(prefix, 'misc')

        # File metadata
        full = media_root / source_path
        ext = Path(source_path).suffix.lstrip('.').upper()
        if ext not in {x.lstrip('.').upper() for x in MEDIA_EXTS}:
            self.skipped += 1
            return

        size_bytes = 0
        width = 0
        height = 0
        try:
            size_bytes = full.stat().st_size
        except OSError:
            self.skipped += 1
            return

        if ext in {'JPG', 'JPEG', 'PNG', 'GIF', 'WEBP', 'BMP'}:
            try:
                from PIL import Image
                with Image.open(full) as img:
                    width, height = img.size
            except Exception:
                pass

        name = Path(source_path).stem[:200]
        usage_summary = ', '.join(usages) if usages else ''
        usage_count = len(usages)
        source_kind = 'linked' if usages else 'imported'

        # Idempotent: dedupe by source_path
        existing = Asset.objects.filter(source_path=source_path).first()
        if existing:
            existing.usage_count = usage_count
            existing.usage_summary = usage_summary
            existing.size_bytes = size_bytes
            if width and height:
                existing.width = width
                existing.height = height
            if not self.dry:
                existing.save(update_fields=['usage_count', 'usage_summary', 'size_bytes', 'width', 'height', 'updated_at'])
            self.updated += 1
            self.stdout.write(f"  ↻ {source_path} → updated ({usage_count} usage(s))")
            return

        # Create new Asset, pointing at the existing file path
        if self.dry:
            self.stdout.write(f"  + {source_path} → folder={folder} usages={usage_count}")
            self.created += 1
            return

        asset = Asset(
            file=source_path,  # Django FileField accepts a relative-to-MEDIA_ROOT string
            name=name,
            folder=folder,
            source=source_kind,
            source_path=source_path,
            format=ext[:10],
            size_bytes=size_bytes,
            width=width,
            height=height,
            usage_count=usage_count,
            usage_summary=usage_summary,
        )
        # Asset.save() auto-skips extraction because format + size_bytes are already populated
        asset.save()
        self.created += 1
        self.stdout.write(self.style.SUCCESS(f"  + {source_path} → folder={folder} usages={usage_count}"))

    @staticmethod
    def _object_label(obj, model, field_name):
        """Build a human-readable usage label like 'Project: Halyk Pay · image'."""
        model_label = model._meta.verbose_name.title() if model._meta.verbose_name else model.__name__
        ident = ''
        for attr in ('title', 'name', 'subject', 'site_title', 'company', 'position', 'email'):
            v = getattr(obj, attr, None)
            if v:
                ident = str(v)[:60]
                break
        if not ident:
            ident = f"#{obj.pk}"
        return f"{model_label}: {ident} · {field_name}"
