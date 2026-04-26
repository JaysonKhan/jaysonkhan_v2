"""Modeltranslation registrations for portfolio models."""
from modeltranslation.translator import register, TranslationOptions
from .models import Project, Skill, Experience, TeamMember


@register(Project)
class ProjectTranslation(TranslationOptions):
    fields = (
        'title',
        'short_description',
        'description_rich',
        'case_study_challenge',
        'case_study_solution',
        'case_study_results',
    )


@register(Skill)
class SkillTranslation(TranslationOptions):
    fields = ('name',)


@register(Experience)
class ExperienceTranslation(TranslationOptions):
    fields = ('company', 'position', 'description', 'location')


@register(TeamMember)
class TeamMemberTranslation(TranslationOptions):
    fields = ('name', 'role', 'bio', 'quote', 'skills')
