from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render
from portfolio.services import PortfolioService, PortfolioRepository
from portfolio.models import Project
from blog.services import BlogService, BlogRepository
from contact.services import ContactService, ContactRepository
from contact.spam_protection import is_honeypot_filled, is_rate_limited
from blog.models import Post
from core.models import SiteSettings


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portfolio_service = PortfolioService(PortfolioRepository())
        context['portfolio'] = portfolio_service.get_portfolio_data()

        blog_service = BlogService(BlogRepository())
        context['latest_posts'] = blog_service.get_all_published_posts()[:3]
        return context


class ProjectListView(AppsGuardMixin, ListView):
    template_name = 'web/projects.html'
    context_object_name = 'projects'
    paginate_by = 10

    _FILTER_TABS = [
        {'key': 'all',    'label': 'All',            'url': '/projects/'},
        {'key': 'cross',  'label': 'Cross-platform', 'url': '/projects/?platform=cross'},
        {'key': 'android','label': 'Android',        'url': '/projects/?platform=android'},
        {'key': 'ios',    'label': 'iOS',             'url': '/projects/?platform=ios'},
        {'key': 'web',    'label': 'Web',             'url': '/projects/?platform=web'},
        {'key': 'bot',    'label': 'Telegram Bot',    'url': '/projects/?is_bot=1'},
    ]

    def get_queryset(self):
        # is_visible filter is already applied in PortfolioRepository,
        # but this view queries directly — keep consistent.
        queryset = Project.objects.filter(is_visible=True).prefetch_related('technologies', 'screenshots')
        platform = self.request.GET.get('platform')
        is_bot = self.request.GET.get('is_bot')
        if is_bot:
            queryset = queryset.filter(is_bot=True)
        elif platform:
            queryset = queryset.filter(platform=platform)
        return queryset.order_by('order', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        platform = self.request.GET.get('platform', '')
        is_bot = self.request.GET.get('is_bot', '')
        if is_bot:
            context['active_filter'] = 'bot'
        elif platform:
            context['active_filter'] = platform
        else:
            context['active_filter'] = 'all'
        context['filter_tabs'] = self._FILTER_TABS
        return context


class ProjectDetailView(AppsGuardMixin, DetailView):
    model = Project
    template_name = 'web/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        # Only visible projects are accessible
        return Project.objects.filter(is_visible=True).prefetch_related('technologies', 'screenshots')


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
        return blog_service.get_post_details(self.kwargs.get('slug'))


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
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        contact_service = ContactService(ContactRepository())
        contact_service.send_contact_message(name, email, subject, message)

        return self.render_to_response(self.get_context_data(success=True))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
