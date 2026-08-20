import json
import logging

from blog.models import Post
from blog.services import BlogRepository, BlogService
from contact.services import ContactRepository, ContactService
from contact.spam_protection import (
    is_honeypot_filled, is_rate_limited, is_spam_content, is_valid_contact,
)
from core.models import PageView
from core.services import SiteSettingsService
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from interactions.models import Comment, Like
from interactions.views import get_tg_profile  # session helper
from portfolio.models import Project
from portfolio.services import PortfolioRepository, PortfolioService

from .bio_copy import NAME_GROUPS, SKILL_GROUPS, get_bio

logger = logging.getLogger(__name__)

# Visitor count cache — avoids COUNT(*) on every page render
_VISITOR_COUNT_CACHE_KEY = 'visitor_count'
_VISITOR_COUNT_TTL = 60 * 60  # 1 hour

# Gallery wall: bir sahifadagi kadrlar soni (server-render ham, JSON feed ham)
GALLERY_PAGE_SIZE = 20


def custom_404_view(request, exception=None):
    """
    Custom 404 handler — shown instead of Django's debug 404 page when DEBUG=False.
    Hides internal URL patterns and stack traces from unauthenticated users.
    """
    try:
        site_settings = SiteSettingsService.get()
    except Exception:
        site_settings = None
    return render(request, 'web/404.html', {'site_settings': site_settings}, status=404)


def custom_500_view(request):
    """
    Custom 500 handler — shown instead of Django's debug 500 page when DEBUG=False.
    Prevents leaking stack traces and settings to users.
    """
    try:
        site_settings = SiteSettingsService.get()
    except Exception:
        site_settings = None
    return render(request, 'web/500.html', {'site_settings': site_settings}, status=500)


def _interactions_context(request, obj):
    """
    Returns like/comment data for a given model instance.
    Passed to template context for BlogDetailView and ProjectDetailView.

    Uses request.tg_profile if already set by the context processor to avoid
    a second TelegramEntity DB lookup on the same request.
    """
    ct = ContentType.objects.get_for_model(obj)
    comments = Comment.objects.filter(
        content_type=ct, object_id=obj.pk, is_approved=True
    ).select_related('author', 'parent', 'parent__author').prefetch_related(
        'reactions', 'reactions__author'
    ).order_by('created_at')

    like_count = Like.objects.filter(content_type=ct, object_id=obj.pk).count()

    # Re-use profile already fetched by the context processor (avoids duplicate PK lookup).
    profile = getattr(request, '_cached_tg_profile', _SENTINEL)
    if profile is _SENTINEL:
        profile = get_tg_profile(request)
        request._cached_tg_profile = profile

    user_liked = (
        Like.objects.filter(author=profile, content_type=ct, object_id=obj.pk).exists()
        if profile else False
    )
    return {
        'comments': comments,
        'like_count': like_count,
        'user_liked': user_liked,
        'app_label': ct.app_label,
        'model_name': ct.model,
        'object_id': obj.pk,
        'tg_profile': profile,  # Ensure profile is always in context for the form
    }


# Sentinel object used to distinguish "not yet cached" from None (not logged in).
_SENTINEL = object()


def _apps_visible():
    """Return True if the Apps section is enabled in SiteSettings."""
    return SiteSettingsService.get().apps_section_visible


class AppsGuardMixin:
    """
    Mixin that blocks access to Apps-related views when
    site_settings.apps_section_visible is False.
    Renders the 'section_unavailable' page instead (HTTP 200 so there's no
    error log noise, but the content is clearly a 'coming soon' message).
    """
    apps_unavailable_message = (
        "The Apps section is temporarily offline. "
        "Come back soon — it'll be up again shortly."
    )

    def dispatch(self, request, *args, **kwargs):
        if not _apps_visible():
            return TemplateView.as_view(
                template_name='web/section_unavailable.html',
                extra_context={'message': self.apps_unavailable_message},
            )(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class HomeView(TemplateView):
    template_name = 'web/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        portfolio_service = PortfolioService(PortfolioRepository())
        context['portfolio'] = portfolio_service.get_homepage_data()

        blog_service = BlogService(BlogRepository())
        context['latest_posts'] = blog_service.get_all_published_posts()[:3]

        # Cached visitor count — avoids COUNT(*) on every request.
        # Visitor rows are created by core.tracking.VisitorTrackingMiddleware
        # (first-touch attribution on every page), not here.
        count = cache.get(_VISITOR_COUNT_CACHE_KEY)
        if count is None:
            count = PageView.objects.count()
            cache.set(_VISITOR_COUNT_CACHE_KEY, count, _VISITOR_COUNT_TTL)
        context['visitor_count'] = count

        # Gallery wall (footer tepasida): 1-sahifa server-render, qolgani
        # gallery_feed JSON orqali silliq qo'shiladi (gallery-wall.js).
        from portfolio.models import GalleryImage

        gallery_qs = GalleryImage.objects.filter(is_visible=True)
        context['gallery_total'] = gallery_qs.count()
        context['gallery_images'] = list(gallery_qs[:GALLERY_PAGE_SIZE])
        return context


class AboutView(TemplateView):
    """`/about/` — the person-entity page.

    Exists so name queries ("Jahongir Qo'ziboyev", "Жахонгир Кузибоев") and
    role queries ("AI dasturchi", "мобильный разработчик") have a single page
    whose title, H1 and body all answer them — the homepage is positioned for
    the product story and cannot carry both.

    Copy is code-owned (`bio_copy.py`), not SiteSettings: the deploy seeders
    must never half-overwrite it.
    """

    template_name = 'web/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bio'] = get_bio(get_language())
        context['name_groups'] = NAME_GROUPS
        context['skill_groups'] = SKILL_GROUPS
        return context


class ProjectListView(AppsGuardMixin, ListView):
    template_name = 'web/projects.html'
    context_object_name = 'projects'
    paginate_by = 10

    # Filter tabs — XIVA INK design kinds, derived from URL fields:
    # 'web'    = has web_page_url (and not a bot)
    # 'bot'    = is_bot flag is True
    # 'mobile' = has app_store_url OR play_store_url

    def get_queryset(self):
        queryset = Project.objects.filter(is_visible=True).prefetch_related('technologies')
        f = self.request.GET.get('filter', '')
        if f == 'web':
            queryset = queryset.filter(web_page_url__gt='', is_bot=False)
        elif f == 'bot':
            queryset = queryset.filter(is_bot=True)
        elif f == 'mobile':
            queryset = queryset.filter(
                Q(app_store_url__gt='') | Q(play_store_url__gt='')
            )
        return queryset.order_by('order', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        f = self.request.GET.get('filter', '')
        context['active_filter'] = f if f in ('web', 'bot', 'mobile') else 'all'
        base = reverse('projects')
        context['filter_tabs'] = [
            {'key': 'all',    'label': _('All'),    'url': base},
            {'key': 'web',    'label': 'Web',       'url': base + '?filter=web'},
            {'key': 'bot',    'label': _('Bots'),   'url': base + '?filter=bot'},
            {'key': 'mobile', 'label': _('Mobile'), 'url': base + '?filter=mobile'},
        ]
        return context


class ProjectDetailView(AppsGuardMixin, DetailView):
    model = Project
    template_name = 'web/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        # Only visible projects are accessible
        return Project.objects.filter(is_visible=True).prefetch_related('technologies')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_interactions_context(self.request, self.object))
        # "Next project" footer link — next visible project in display order, wraps around
        ordered = list(
            Project.objects.filter(is_visible=True)
            .order_by('order', '-created_at')
            .values_list('pk', flat=True)
        )
        if len(ordered) > 1:
            idx = ordered.index(self.object.pk) if self.object.pk in ordered else 0
            context['next_project'] = Project.objects.get(pk=ordered[(idx + 1) % len(ordered)])
        # Channel share info (admin only)
        if self.request.user.is_staff:
            from interactions.notifications.channel_share import ChannelShareService
            context['channel_share_info'] = ChannelShareService().get_share_info(self.object)
        return context


class BlogListView(ListView):
    template_name = 'web/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        blog_service = BlogService(BlogRepository())
        return blog_service.get_all_published_posts()


class BlogDetailView(DetailView):
    model = Post
    template_name = 'web/blog_detail.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        blog_service = BlogService(BlogRepository())
        post = blog_service.get_post_details(self.kwargs.get('slug'))
        if post is None:
            raise Http404("Post not found")
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_interactions_context(self.request, self.object))
        # Related posts by shared tags
        blog_service = BlogService(BlogRepository())
        context['related_posts'] = blog_service.get_related_posts(self.object)
        # Channel share info (admin only)
        if self.request.user.is_staff:
            from interactions.notifications.channel_share import ChannelShareService
            context['channel_share_info'] = ChannelShareService().get_share_info(self.object)
        return context


class BlogSearchView(ListView):
    template_name = 'web/blog_search.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        if not q:
            return Post.objects.none()
        blog_service = BlogService(BlogRepository())
        return blog_service.search_posts(q)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class TeamView(TemplateView):
    template_name = 'web/team.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        members = PortfolioRepository.get_visible_team()
        context['team_members'] = members
        context['team_payload'] = {
            str(m.pk): {
                'id': m.pk,
                'name': m.name,
                'role': m.role,
                'bio': m.bio,
                'quote': m.quote or '',
                'years': m.years_experience,
                'initials': m.initials,
                'photo': m.photo.url if m.photo else '',
                # real portret — modal'da anime bosilganda ochiladi (lightbox patterni)
                'photo_real': m.photo_real.url if m.photo_real else '',
                'skills': m.skills_list,
                'telegram': m.telegram_url or '',
                'github': m.github_url or '',
                'linkedin': m.linkedin_url or '',
            }
            for m in members
        }
        return context


class ContactView(TemplateView):
    template_name = 'web/contact.html'

    def post(self, request, *args, **kwargs):
        # -- Spam protection --
        if is_honeypot_filled(request):
            # Silently reject: return success to not tip off bots
            return self.render_to_response(self.get_context_data(success=True))

        if is_rate_limited(request):
            messages.error(
                request,
                "Too many messages sent. Please try again in a few minutes."
            )
            return self.render_to_response(self.get_context_data(form_data=request.POST))

        # -- Normal processing --
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        # v4 form has no subject field — derive one from the message head
        subject = request.POST.get('subject', '').strip() or message[:80]

        if not all([name, email, message]):
            messages.error(request, "Please fill in all required fields.")
            return self.render_to_response(self.get_context_data(form_data=request.POST))

        # A real typo deserves a visible error; bots ignore it either way. The
        # SSR path writes via objects.create(), which never runs full_clean(),
        # so without this the EmailField happily stored bot garbage.
        if not is_valid_contact(email):
            messages.error(
                request,
                "Please enter a valid email address or Telegram username."
            )
            return self.render_to_response(self.get_context_data(form_data=request.POST))

        # Silently pretend it worked: an error tells the sender to retune.
        if is_spam_content(request, message):
            return self.render_to_response(self.get_context_data(success=True))

        try:
            contact_service = ContactService(ContactRepository())
            contact_service.send_contact_message(name, email, subject, message)
        except Exception:
            logger.exception('Contact form submission failed')
            messages.error(request, 'Something went wrong. Please try again later.')
            return self.render_to_response(self.get_context_data(form_data=request.POST))

        return self.render_to_response(self.get_context_data(success=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # "Quyosh sistemasi": saytga Telegram orqali kirgan mehmonlar.
        # Rasmlilardan 12 tasi — sayyoralar; keyingi 6 tasi — mini-yo'ldoshlar
        # (yo'ldosh rasmsiz bo'lsa initial harf ko'rinadi).
        from telegram.models import TelegramEntity

        site_users = list(
            TelegramEntity.objects.filter(
                sources__service='site', entity_type='user',
            ).order_by('-updated_at').distinct()[:30]
        )
        with_photo = [u for u in site_users if u.photo_url]
        without_photo = [u for u in site_users if not u.photo_url]
        context['orbit_guests'] = with_photo[:12]
        context['orbit_moons'] = (with_photo[12:] + without_photo)[:6]
        return context


class GalleryFeedView(View):
    """GET gallery/feed/?page=N — gallery wall'ning keyingi sahifasi (JSON).

    i18n_patterns ichida (til-prefiksli URL) — hint'lar sahifa tilida keladi
    (CLAUDE.md gotcha #12: qo'lda yozilgan prefikssiz yo'l POSTni sindiradi,
    GETda esa tilni yo'qotadi; template {% url %} bilan uzatadi).
    """

    def get(self, request):
        from portfolio.models import GalleryImage

        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (TypeError, ValueError):
            page = 1

        qs = GalleryImage.objects.filter(is_visible=True)
        paginator = Paginator(qs, GALLERY_PAGE_SIZE)
        page_obj = paginator.get_page(page)

        return JsonResponse({
            'images': [
                {
                    # url = devorda ko'rinadigan rasm (cover bo'lsa cover, bo'lmasa original)
                    'url': g.display_url,
                    'ar': g.display_aspect_css,
                    'w': g.display_width,
                    'h': g.display_height,
                    # full = lightbox'da ochiladigan asosiy (original) rasm
                    'full': g.image.url,
                    'full_ar': g.aspect_css,
                    'hint': g.hint or '',
                }
                for g in page_obj.object_list
            ],
            'has_next': page_obj.has_next(),
            'total': paginator.count,
        })


# -- Telegram Mini App router --


class TgAppRouterView(View):
    """Telegram Mini App deep link router + auto-login trampoline.

    BotFather da ``/newapp`` bilan ro'yxatdan o'tgan Mini App shu
    URL ga yo'naltiriladi.

    Deep link format: ``https://t.me/{bot}/{app}?startapp={param}``

    Muammo: Server-side 302 redirect ``initData`` ni yo'qotadi (URL hash
    fragment serverga yuborilmaydi, redirect qilganda yo'qoladi).

    Yechim: "Trampoline" sahifa -- avval ``initData`` bilan auto-login
    qiladi, so'ng JS orqali target sahifaga yo'naltiradi.  Agar user
    allaqachon login bo'lgan bo'lsa yoki Telegram konteksti yo'q bo'lsa,
    darhol redirect qiladi.

    Parametrlar:
        c-{id}         -> Kommentga o'tish (post/project sahifasida)
        post-{slug}    -> Blog post
        proj-{slug}    -> Project
        home           -> Bosh sahifa
    """

    # Minimal HTML that does auto-login before navigating away.
    # %(target)s and %(login)s are filled with json.dumps() values.
    _TRAMPOLINE = (
        '<!DOCTYPE html>'
        '<html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<script src="https://telegram.org/js/telegram-web-app.js"></script>'
        '<style>body{margin:0;display:flex;justify-content:center;'
        'align-items:center;height:100vh;background:#0f172a;'
        'color:#94a3b8;font-family:sans-serif}</style>'
        '</head><body><p>Loading…</p><script>'
        '(function(){'
        'var t=%(target)s,u=%(login)s;'
        'if(window.Telegram&&window.Telegram.WebApp){'
        'window.Telegram.WebApp.ready();window.Telegram.WebApp.expand()}'
        'if(window.Telegram&&window.Telegram.WebApp'
        '&&window.Telegram.WebApp.initData){'
        'fetch(u,{method:"POST",credentials:"same-origin",'
        'headers:{"Content-Type":"application/json"},'
        'body:JSON.stringify({init_data:window.Telegram.WebApp.initData})})'
        '.then(function(){window.location.replace(t)})'
        '.catch(function(){window.location.replace(t)})'
        '}else{window.location.replace(t)}'
        '})();'
        '</script></body></html>'
    )

    def get(self, request):
        start = request.GET.get('tgWebAppStartParam', '')
        target_url = self._resolve_target(start)

        # Already logged in — skip trampoline, redirect immediately
        if get_tg_profile(request):
            return redirect(target_url)

        # Render trampoline: auto-login via initData -> JS redirect
        login_url = reverse('interactions:telegram_webapp_login')
        html = self._TRAMPOLINE % {
            'target': json.dumps(target_url),
            'login': json.dumps(login_url),
        }
        return HttpResponse(html, content_type='text/html')

    @staticmethod
    def _resolve_target(start: str) -> str:
        """Map ``startapp`` parameter to a local URL path.

        Unknown prefixes fall through to the home page.
        """

        # Comment deep link
        if start.startswith('c-'):
            try:
                comment_id = int(start[2:])
                comment = Comment.objects.select_related(
                    'content_type',
                ).get(pk=comment_id)
                obj = comment.content_object
                if obj and hasattr(obj, 'get_absolute_url'):
                    return f'{obj.get_absolute_url()}#comment-{comment_id}'
            except (ValueError, TypeError, Comment.DoesNotExist):
                pass

        # Blog post deep link
        if start.startswith('post-'):
            slug = start[5:]
            if slug:
                try:
                    return reverse('blog_detail', kwargs={'slug': slug})
                except Exception:
                    pass

        # Project deep link
        if start.startswith('proj-'):
            slug = start[5:]
            if slug:
                try:
                    return reverse('project_detail', kwargs={'slug': slug})
                except Exception:
                    pass

        # Default — home page
        return reverse('home')
