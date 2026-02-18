from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Skill, Project, Experience


@admin.register(Skill)
class SkillAdmin(UnfoldModelAdmin):
    list_display = ('name', 'level')
    search_fields = ('name',)
    list_filter = ('level',)


@admin.register(Project)
class ProjectAdmin(UnfoldModelAdmin):
    list_display = ('title', 'order', 'created_at')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description')
    filter_horizontal = ('technologies',)
    list_filter = ('created_at',)


@admin.register(Experience)
class ExperienceAdmin(UnfoldModelAdmin):
    list_display = ('position', 'company', 'start_date', 'is_current')
    list_filter = ('company', 'is_current')
    search_fields = ('position', 'company')
