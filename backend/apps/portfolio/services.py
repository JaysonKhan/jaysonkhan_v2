from .models import Project, Skill, Experience, TeamMember


class PortfolioRepository:
    @staticmethod
    def get_all_projects():
        return (
            Project.objects
            .filter(is_visible=True)
            .prefetch_related('technologies')
            .order_by('order', '-created_at')
        )

    @staticmethod
    def get_featured_projects():
        return (
            Project.objects
            .filter(is_featured=True, is_visible=True)
            .prefetch_related('technologies')
            .order_by('order', '-created_at')
        )

    @staticmethod
    def get_web_projects():
        """Projects that have a web_page_url."""
        return (
            Project.objects
            .filter(web_page_url__gt='', is_visible=True)
            .prefetch_related('technologies')
            .order_by('order', '-created_at')
        )

    @staticmethod
    def get_bot_projects():
        """Projects flagged as Telegram bots."""
        return (
            Project.objects
            .filter(is_bot=True, is_visible=True)
            .prefetch_related('technologies')
            .order_by('order', '-created_at')
        )

    @staticmethod
    def get_all_skills():
        return (
            Skill.objects
            .only('id', 'name', 'category', 'order')
            .all()
        )

    @staticmethod
    def get_skills_grouped():
        """Return skills grouped by category as {category_label: [skills]}."""
        skills = (
            Skill.objects
            .only('id', 'name', 'category', 'order')
            .order_by('category', 'order', 'name')
        )
        grouped: dict = {}
        for skill in skills:
            label = skill.get_category_display()
            grouped.setdefault(label, []).append(skill)
        return grouped

    @staticmethod
    def get_all_experience():
        return Experience.objects.select_related().order_by('-start_date')

    @staticmethod
    def get_visible_team():
        return TeamMember.objects.filter(is_visible=True).order_by('order', 'id')


class PortfolioService:
    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def get_portfolio_data(self) -> dict:
        return {
            'projects': self.repository.get_all_projects(),
            'featured_projects': self.repository.get_featured_projects(),
            'web_projects': self.repository.get_web_projects(),
            'bot_projects': self.repository.get_bot_projects(),
            'skills': self.repository.get_all_skills(),
            'skills_grouped': self.repository.get_skills_grouped(),
            'experience': self.repository.get_all_experience(),
        }

    def get_homepage_data(self) -> dict:
        """Lightweight version — only data needed for the homepage."""
        featured = self.repository.get_featured_projects()
        return {
            'featured_projects': featured,
            # Fallback if none are marked as featured — template uses this
            'projects': self.repository.get_all_projects()[:3] if not featured else [],
            'skills_grouped': self.repository.get_skills_grouped(),
            'experience': self.repository.get_all_experience(),
        }
