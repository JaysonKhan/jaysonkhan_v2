from .models import Project, Skill, Experience

class PortfolioRepository:
    @staticmethod
    def get_all_projects():
        return Project.objects.prefetch_related('technologies').all()

    @staticmethod
    def get_all_skills():
        return Skill.objects.all()

    @staticmethod
    def get_all_experience():
        return Experience.objects.all()

class PortfolioService:
    def __init__(self, repository: PortfolioRepository):
        self.repository = repository

    def get_portfolio_data(self):
        return {
            'projects': self.repository.get_all_projects(),
            'skills': self.repository.get_all_skills(),
            'experience': self.repository.get_all_experience(),
        }
