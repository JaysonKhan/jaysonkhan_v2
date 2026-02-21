from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from portfolio.services import PortfolioService, PortfolioRepository
from portfolio.models import Project
from blog.services import BlogService, BlogRepository
from contact.services import ContactService, ContactRepository
from contact.spam_protection import is_honeypot_filled, is_rate_limited
from blog.models import Post


class HomeView(TemplateView):
    template_name = 'web/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portfolio_service = PortfolioService(PortfolioRepository())
        context['portfolio'] = portfolio_service.get_portfolio_data()

        blog_service = BlogService(BlogRepository())
        context['latest_posts'] = blog_service.get_all_published_posts()[:3]
        return context


class ProjectListView(ListView):
    template_name = 'web/projects.html'
    context_object_name = 'projects'
    paginate_by = 10

    def get_queryset(self):
        portfolio_service = PortfolioService(PortfolioRepository())
        return portfolio_service.repository.get_all_projects()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Platform filter
        platform = self.request.GET.get('platform')
        if platform:
            context['projects'] = context['projects'].filter(platform=platform)
            context['active_platform'] = platform
        return context


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'web/project_detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        return Project.objects.prefetch_related('technologies', 'screenshots')


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

