"""Modeltranslation registrations for portfolio models."""
from modeltranslation.translator import register, TranslationOptions
from .models import Project, Skill, Experience, TeamMember, GalleryImage


@register(Project)
class ProjectTranslation(TranslationOptions):
    fallback_undefined = ''
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
    fallback_undefined = ''
    fields = ('name',)


@register(Experience)
class ExperienceTranslation(TranslationOptions):
    fallback_undefined = ''
    fields = ('company', 'position', 'description', 'location')


@register(TeamMember)
class TeamMemberTranslation(TranslationOptions):
    fallback_undefined = ''
    fields = ('name', 'role', 'bio', 'quote', 'skills')


@register(GalleryImage)
class GalleryImageTranslation(TranslationOptions):
    fallback_undefined = ''
    fields = ('hint',)
