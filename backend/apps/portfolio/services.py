from itertools import groupby
from .models import Project, Skill, Experience


class PortfolioRepository:
    @staticmethod
    def get_all_projects():
        return Project.objects.prefetch_related('technologies', 'screenshots').all()

    @staticmethod
    def get_featured_projects():
        return (
            Project.objects
            .filter(is_featured=True)
            .prefetch_related('technologies', 'screenshots')
        )

    @staticmethod
    def get_all_skills():
        return Skill.objects.only('id', 'name', 'level', 'icon', 'category', 'order', 'show_in_hero').all()

    @staticmethod
    def get_hero_skills():
        """Return skills marked for hero orbit display, ordered by order field."""
        return (
            Skill.objects
            .filter(show_in_hero=True)
            .only('id', 'name', 'icon', 'order')
            .order_by('order', 'name')
        )

    @staticmethod
    def get_skills_grouped():
        """Return skills grouped by category as {category_label: [skills]}."""
        skills = Skill.objects.all()
        grouped = {}
        for skill in skills:
            label = skill.get_category_display()
            grouped.setdefault(label, []).append(skill)
        return grouped

    @staticmethod
    def get_all_experience():
        return Experience.objects.all()


class PortfolioService:
    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def get_portfolio_data(self):
        return {
            'projects': self.repository.get_all_projects(),
            'featured_projects': self.repository.get_featured_projects(),
            'skills': self.repository.get_all_skills(),
            'skills_grouped': self.repository.get_skills_grouped(),
            'hero_skills': self.repository.get_hero_skills(),
            'experience': self.repository.get_all_experience(),
        }
