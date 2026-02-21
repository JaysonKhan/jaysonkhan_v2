from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import Truncator
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
    list_display = ('name', 'icon_display', 'category', 'level', 'order')
    list_editable = ('category', 'level', 'order')
    list_filter = ('category',)
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'icon', 'category', 'level', 'order'),
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


@admin.register(Project)
class ProjectAdmin(UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('thumbnail', 'title', 'short_desc', 'platform', 'is_featured', 'order')
    list_display_links = ('thumbnail', 'title')
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

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="48" height="48" '
                'style="border-radius:8px;object-fit:cover;'
                'border:1px solid rgba(255,255,255,.12);" />',
                obj.image.url,
            )
        return format_html(
            '<div style="width:48px;height:48px;border-radius:8px;'
            'background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:18px;">📱</div>'
        )
    thumbnail.short_description = ''

    def short_desc(self, obj):
        text = obj.short_description or obj.description
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
