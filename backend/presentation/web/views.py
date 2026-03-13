import uuid

from django.core.cache import cache
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from portfolio.services import PortfolioService, PortfolioRepository
from portfolio.models import Project
from blog.services import BlogService, BlogRepository
from contact.services import ContactService, ContactRepository
from contact.spam_protection import is_honeypot_filled, is_rate_limited
from blog.models import Post
from core.models import SiteSettings, PageView
from interactions.models import Comment, Like
from interactions.views import get_tg_profile  # session helper

# Visitor count cache — avoids COUNT(*) on every page render
_VISITOR_COUNT_CACHE_KEY = 'visitor_count'
_VISITOR_COUNT_TTL = 60 * 60  # 1 hour


def custom_404_view(request, exception=None):
    """
    Custom 404 handler — shown instead of Django's debug 404 page when DEBUG=False.
    Hides internal URL patterns and stack traces from unauthenticated users.
    """
    return render(request, 'web/404.html', status=404)


def custom_500_view(request):
    """
    Custom 500 handler — shown instead of Django's debug 500 page when DEBUG=False.
    Prevents leaking stack traces and settings to users.
    """
    return render(request, 'web/500.html', status=500)


def _interactions_context(request, obj):
    """
    Returns like/comment data for a given model instance.
    Passed to template context for BlogDetailView and ProjectDetailView.
    """
    ct = ContentType.objects.get_for_model(obj)
    # Get only top-level comments (parent=None) to build the tree in template, 
    # or just prefetch all and handle nested in template. 
    # Telegram style usually shows a thread or a simple flat list with 'reply' references.
    # We'll prefetch all approved comments for this object.
    comments = Comment.objects.filter(
        content_type=ct, object_id=obj.pk, is_approved=True
    ).select_related('author', 'parent', 'parent__author').prefetch_related('reactions', 'reactions__author').order_by('created_at')
    
    like_count = Like.objects.filter(content_type=ct, object_id=obj.pk).count()

    profile = get_tg_profile(request)
    user_liked = (
        Like.objects.filter(author=profile, content_type=ct, object_id=obj.pk).exists()
        if profile else False
    )
    return {
        'comments':   comments,
        'like_count': like_count,
        'user_liked': user_liked,
        'app_label':  ct.app_label,
        'model_name': ct.model,
        'object_id':  obj.pk,
        'tg_profile': profile, # Ensure profile is always in context for the form
    }


def _apps_visible():
    """Return True if the Apps section is enabled in SiteSettings."""
    return SiteSettings.load().apps_section_visible


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

    VISITOR_COOKIE = 'jk_visitor'
    COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 year

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        portfolio_service = PortfolioService(PortfolioRepository())
        context['portfolio'] = portfolio_service.get_homepage_data()

        blog_service = BlogService(BlogRepository())
        context['latest_posts'] = blog_service.get_all_published_posts()[:3]

        # Cached visitor count — avoids COUNT(*) on every request
        count = cache.get(_VISITOR_COUNT_CACHE_KEY)
        if count is None:
            count = PageView.objects.count()
            cache.set(_VISITOR_COUNT_CACHE_KEY, count, _VISITOR_COUNT_TTL)
        context['visitor_count'] = count
        return context

    @staticmethod
    def _get_client_ip(request):
        """Extract real client IP (handles reverse proxy X-Forwarded-For)."""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        visitor_id = request.COOKIES.get(self.VISITOR_COOKIE)
        ip = self._get_client_ip(request)

        if visitor_id:
            # Case 1: Cookie exists — returning visitor (same browser)
            # Ensure DB record still exists (cookie might outlive DB reset)
            try:
                uid = uuid.UUID(visitor_id)
            except ValueError:
                uid = uuid.uuid4()
            if not PageView.objects.filter(visitor_id=uid).exists():
                PageView.objects.create(visitor_id=uid, ip_address=ip)
                cache.delete(_VISITOR_COUNT_CACHE_KEY)
        elif ip and PageView.objects.filter(ip_address=ip).exists():
            # Case 2: No cookie but IP already seen — different browser / incognito
            # Link to existing record via cookie, don't create new (no cache bust)
            existing = PageView.objects.filter(ip_address=ip).first()
            response.set_cookie(
                self.VISITOR_COOKIE,
                str(existing.visitor_id),
                max_age=self.COOKIE_MAX_AGE,
                httponly=True,
                samesite='Lax',
            )
        else:
            # Case 3: No cookie, new IP — genuinely new visitor
            new_id = uuid.uuid4()
            PageView.objects.create(visitor_id=new_id, ip_address=ip)
            cache.delete(_VISITOR_COUNT_CACHE_KEY)
            response.set_cookie(
                self.VISITOR_COOKIE,
                str(new_id),
                max_age=self.COOKIE_MAX_AGE,
                httponly=True,
                samesite='Lax',
            )

        return response


class ProjectListView(AppsGuardMixin, ListView):
    template_name = 'web/projects.html'
    context_object_name = 'projects'
    paginate_by = 10

    # Filter tabs — filtering is now done by URL fields, not the platform type field.
    # 'cross'   = has both play_store_url AND app_store_url
    # 'android' = has play_store_url (includes cross-platform)
    # 'ios'     = has app_store_url  (includes cross-platform)
    # 'web'     = has web_page_url
    # 'bot'     = is_bot flag is True
    _FILTER_TABS = [
        {'key': 'all',     'label': 'All',            'url': '/projects/'},
        {'key': 'cross',   'label': 'Cross-platform', 'url': '/projects/?filter=cross'},
        {'key': 'android', 'label': 'Android',        'url': '/projects/?filter=android'},
        {'key': 'ios',     'label': 'iOS',             'url': '/projects/?filter=ios'},
        {'key': 'web',     'label': 'Web',             'url': '/projects/?filter=web'},
        {'key': 'bot',     'label': 'Telegram Bot',    'url': '/projects/?filter=bot'},
    ]

    def get_queryset(self):
        queryset = Project.objects.filter(is_visible=True).prefetch_related('technologies')
        f = self.request.GET.get('filter', '')
        if f == 'cross':
            # Must have both store URLs
            queryset = queryset.filter(
                play_store_url__gt='', app_store_url__gt=''
            )
        elif f == 'android':
            queryset = queryset.filter(play_store_url__gt='')
        elif f == 'ios':
            queryset = queryset.filter(app_store_url__gt='')
        elif f == 'web':
            queryset = queryset.filter(web_page_url__gt='')
        elif f == 'bot':
            queryset = queryset.filter(is_bot=True)
        return queryset.order_by('order', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        f = self.request.GET.get('filter', '')
        context['active_filter'] = f if f in ('cross', 'android', 'ios', 'web', 'bot') else 'all'
        context['filter_tabs'] = self._FILTER_TABS
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


class ContactView(TemplateView):
    template_name = 'web/contact.html'

    def post(self, request, *args, **kwargs):
        # ── Spam protection ──────────────────────────────────────────────────
        if is_honeypot_filled(request):
            # Silently reject: return success to not tip off bots
            return self.render_to_response(self.get_context_data(success=True))

        if is_rate_limited(request):
            messages.error(
                request,
                "Too many messages sent. Please try again in a few minutes."
            )
            return self.render_to_response(self.get_context_data())

        # ── Normal processing ────────────────────────────────────────────────
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not all([name, email, subject, message]):
            messages.error(request, "Please fill in all required fields.")
            return self.render_to_response(self.get_context_data())

        contact_service = ContactService(ContactRepository())
        contact_service.send_contact_message(name, email, subject, message)

        return self.render_to_response(self.get_context_data(success=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
