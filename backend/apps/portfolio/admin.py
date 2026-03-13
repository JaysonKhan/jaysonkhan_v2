from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Skill, Project, Experience
from django import forms
from core.widgets import RichTextWidget
from django.utils.safestring import mark_safe

@admin.register(Skill)
class SkillAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('name', 'icon_display', 'category', 'level', 'order', 'show_in_hero')
    list_editable = ('category', 'level', 'order', 'show_in_hero')
    list_filter = ('category', 'show_in_hero')
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'icon', 'category', 'level', 'order', 'show_in_hero'),
        }),
    )

    def icon_display(self, obj):
        if obj.icon:
            return format_html(
                '<code style="font-size:11px;opacity:.7;">{}</code>',
                obj.icon,
            )
        return '—'
    icon_display.short_description = 'Icon'


class ProjectAdminForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        widgets = {
            'description_rich': RichTextWidget(),
        }

@admin.register(Project)
class ProjectAdmin(UnfoldModelAdmin):
    form = ProjectAdminForm
    list_per_page = 10
    list_display = ('thumbnail', 'title', 'short_desc', 'is_bot', 'is_featured', 'is_visible', 'order')
    list_display_links = ('thumbnail', 'title')
    list_editable = ('order', 'is_featured', 'is_bot', 'is_visible')
    list_filter = ('is_featured', 'is_bot', 'is_visible', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description_rich')
    filter_horizontal = ('technologies',)

    fieldsets = (
        ('Basic Info', {
            'fields': (
                'title', 'slug', 'short_description', 'description_rich',
                'image', 'is_featured', 'is_visible', 'order',
            ),
        }),
        ('Store Links', {
            'fields': (
                'app_store_url', 'play_store_url',
                'web_page_url',
                'is_bot',
            ),
            'description': (
                'Fill in the relevant store URLs. '
                'is_bot=True → also shows in the Bot section.'
            ),
        }),
        ('Links & Technologies', {
            'fields': ('github_url', 'technologies'),
        }),
        ('Case Study', {
            'fields': (
                'case_study_challenge',
                'case_study_solution',
                'case_study_results',
            ),
            'description': (
                'Optional structured case study. '
                'Fill any field to show a Case Study section on the detail page.'
            ),
            'classes': ('collapse',),
        }),
    )

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="48" height="48" '
                'style="border-radius:8px;object-fit:cover;'
                'border:1px solid rgba(255,255,255,.12);" />',
                obj.image.url,
            )
        return mark_safe(
            '<div style="width:48px;height:48px;border-radius:8px;'
            'background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:18px;">📱</div>'
        )
    thumbnail.short_description = ''

    def short_desc(self, obj):
        text = obj.get_card_description()
        return Truncator(text).chars(60)
    short_desc.short_description = 'Description'


@admin.register(Experience)
class ExperienceAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('position', 'company', 'location', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current',)
    search_fields = ('position', 'company', 'location')

    fieldsets = (
        (None, {
            'fields': (
                'company', 'position', 'location',
                'company_logo', 'company_url',
                'description',
                'start_date', 'end_date', 'is_current',
            ),
        }),
    )
