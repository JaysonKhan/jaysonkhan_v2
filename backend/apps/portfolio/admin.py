from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldModelAdmin, TabularInline as UnfoldTabularInline
from .models import Skill, Project, ProjectScreenshot, Experience


class ProjectScreenshotInline(UnfoldTabularInline):
    model = ProjectScreenshot
    extra = 1
    fields = ('image', 'caption', 'order', 'screenshot_preview')
    readonly_fields = ('screenshot_preview',)

    def screenshot_preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" height="80" style="border-radius:8px;'
                'border:1px solid rgba(255,255,255,.15);" />',
                obj.image.url,
            )
        return '—'
    screenshot_preview.short_description = 'Preview'


@admin.register(Skill)
class SkillAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('name', 'category', 'level', 'order')
    list_editable = ('category', 'level', 'order')
    list_filter = ('category',)
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'icon', 'category', 'level', 'order'),
        }),
    )


@admin.register(Project)
class ProjectAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('title', 'platform', 'is_featured', 'order', 'created_at')
    list_editable = ('order', 'is_featured')
    list_filter = ('platform', 'is_featured', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description', 'tech_stack')
    filter_horizontal = ('technologies',)
    inlines = [ProjectScreenshotInline]

    fieldsets = (
        ('Basic Info', {
            'fields': (
                'title', 'slug', 'short_description', 'description',
                'image', 'is_featured', 'order',
            ),
        }),
        ('Mobile / Platform', {
            'fields': (
                'platform', 'tech_stack',
                'app_store_url', 'play_store_url',
            ),
            'description': 'Mobile-specific fields: platform, store links, tech stack.',
        }),
        ('Links & Technologies', {
            'fields': ('github_url', 'live_url', 'technologies'),
        }),
    )


@admin.register(Experience)
class ExperienceAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('position', 'company', 'location', 'start_date', 'is_current')
    list_filter = ('company', 'is_current')
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
