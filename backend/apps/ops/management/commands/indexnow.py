"""IndexNow — tell Bing/Yandex which public URLs changed.

IndexNow (api.indexnow.org) shares one POST with every participating engine
(Bing, Yandex, Seznam, Naver). Google does not take part (sitemap + lastmod).

Follows the sitemap: static pages, projects and blog posts × 4 locales. A URL
is submitted when the content it renders differs from what IndexNow last
accepted (`ops.IndexNowUrl`), or when it left the sitemap (so the engines drop
it). Nothing changed → no request. A rejected POST records nothing, so the
next run retries the same URLs.

    manage.py indexnow              # changed URLs, at most --limit per run
    manage.py indexnow --dry-run    # list them, send nothing
    manage.py indexnow --all        # every sitemap URL (after a redesign)

First run: every URL is new, so --limit is the first-run cap; whatever is left
drains on the following runs.

Run it on the server — a local DB has other content, use --dry-run there.

The very first POST can answer 403 SiteVerificationNotCompleted while IndexNow
is still fetching /<key>.txt. Not a bug: the next run passes.
"""
from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
from blog.models import Post
from core.models import SiteSettings, TelegramMixin
from core.sitemaps import SITE_BASE, SITEMAPS
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils import translation
from modeltranslation.fields import TranslationField
from ops.models import IndexNowUrl
from portfolio.models import Experience, GalleryImage, Project, TeamMember
from presentation.web.bio_copy import get_bio

ENDPOINT = 'https://api.indexnow.org/indexnow'
HOST = urlsplit(SITE_BASE).netloc
DEFAULT_LIMIT = 100

# Columns that churn without the rendered page changing: timestamps, the
# WakaTime cron's stats, the bot's own settings (toggled from Telegram).
VOLATILE = {'updated_at', 'wakatime_stats'} | {f.attname for f in TelegramMixin._meta.fields}

# Rows a static page lists, on top of SiteSettings (header, footer, page copy).
VISIBLE = {
    Project: lambda: Project.objects.filter(is_visible=True),
    Post: lambda: Post.objects.filter(is_published=True),
    TeamMember: lambda: TeamMember.objects.filter(is_visible=True),
    GalleryImage: lambda: GalleryImage.objects.filter(is_visible=True),
    Experience: lambda: Experience.objects.all(),
}
STATIC_DEPS = {
    'home': (Project, Post, GalleryImage, Experience),
    'projects': (Project,),
    'blog_list': (Post,),
    'team': (TeamMember,),
}


def _row(obj, lang):
    """One DB row as the page renders it in `lang` (xo fallbacks resolved)."""
    with translation.override(lang):
        return {
            f.attname: str(getattr(obj, f.attname))
            for f in obj._meta.concrete_fields
            if not isinstance(f, TranslationField) and f.attname not in VOLATILE
        }


def page_states():
    """{absolute URL: content fingerprint} for every sitemap entry."""
    site = SiteSettings.load()
    listed = {}

    def rows(model, lang):
        if (model, lang) not in listed:
            listed[model, lang] = [_row(obj, lang) for obj in VISIBLE[model]()]
        return listed[model, lang]

    states = {}
    for sitemap_cls in SITEMAPS.values():
        sitemap = sitemap_cls()
        for page in sitemap.paginator.page_range:
            for entry in sitemap.get_urls(page=page, site=SimpleNamespace(domain=HOST), protocol='https'):
                item, lang = entry['item']
                parts = [_row(site, lang)]
                if isinstance(item, models.Model):
                    parts.append(_row(item, lang))
                else:  # StaticSitemap.PAGES entry: (url name, priority, changefreq)
                    parts += [rows(model, lang) for model in STATIC_DEPS.get(item[0], ())]
                    if item[0] == 'about':  # copy is code-owned, not in the DB
                        parts.append(get_bio(lang))
                payload = json.dumps(parts, sort_keys=True, default=str)
                states[entry['location']] = hashlib.sha1(payload.encode()).hexdigest()
    return states


class Command(BaseCommand):
    help = 'Submit changed public URLs to IndexNow (Bing/Yandex).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                            help=f'Max URLs per run — the first-run cap (default: {DEFAULT_LIMIT}).')
        parser.add_argument('--all', action='store_true',
                            help='Resubmit every sitemap URL, changed or not.')
        parser.add_argument('--dry-run', action='store_true',
                            help='List what would be submitted; send nothing.')

    def handle(self, *args, **opts):
        states = page_states()
        known = dict(IndexNowUrl.objects.values_list('url', 'fingerprint'))
        changed = [url for url, fp in states.items() if opts['all'] or known.get(url) != fp]
        gone = [url for url in known if url not in states]
        batch = (changed + gone)[:max(opts['limit'], 0)]
        if not batch:
            self.stdout.write(self.style.SUCCESS(f'Nothing changed — {len(states)} URLs up to date.'))
            return

        self.stdout.write(
            f'{len(changed)} changed + {len(gone)} removed of {len(states)} sitemap URLs; '
            f'submitting {len(batch)}.'
        )
        if opts['dry_run']:
            for url in batch:
                self.stdout.write(f'  {url}')
            self.stdout.write(self.style.SUCCESS('DRY-RUN — nothing sent.'))
            return

        key = settings.INDEXNOW_KEY
        try:
            resp = httpx.post(ENDPOINT, timeout=30, json={
                'host': HOST,
                'key': key,
                'keyLocation': f'{SITE_BASE}/{key}.txt',
                'urlList': batch,
            })
        except httpx.HTTPError as exc:
            raise CommandError(f'IndexNow network error: {exc}') from exc
        if not resp.is_success:
            raise CommandError(f'IndexNow HTTP {resp.status_code}: {resp.text[:200]}')

        for url in batch:
            if url in states:
                IndexNowUrl.objects.update_or_create(url=url, defaults={'fingerprint': states[url]})
            else:
                IndexNowUrl.objects.filter(url=url).delete()
        self.stdout.write(self.style.SUCCESS(f'Submitted {len(batch)} URLs (HTTP {resp.status_code}).'))
