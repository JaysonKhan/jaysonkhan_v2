from core.widgets import RichTextWidget
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from modeltranslation.admin import TranslationAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin

from .models import Experience, GalleryImage, Project, Skill, TeamMember


@admin.register(Skill)
class SkillAdmin(TranslationAdmin, UnfoldModelAdmin):
    list_per_page = 10
    list_display = ('name', 'category', 'order')
    list_editable = ('category', 'order')
    list_filter = ('category',)
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'order'),
        }),
    )


class ProjectAdminForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        widgets = {
            'description_rich_xo': RichTextWidget(),
            'description_rich_uz': RichTextWidget(),
            'description_rich_ru': RichTextWidget(),
            'description_rich_en': RichTextWidget(),
        }

@admin.register(Project)
class ProjectAdmin(TranslationAdmin, UnfoldModelAdmin):
    form = ProjectAdminForm
    list_per_page = 10
    list_display = ('thumbnail', 'title', 'short_desc', 'is_bot', 'is_featured', 'is_visible', 'order')
    list_display_links = ('thumbnail', 'title')
    list_editable = ('order', 'is_featured', 'is_bot', 'is_visible')
    list_filter = ('is_featured', 'is_bot', 'is_visible', 'created_at')
    prepopulated_fields = {'slug': ('title_xo',)}
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
                'stats',
            ),
            'description': (
                'Optional structured case study. '
                'Fill any field to show a Case Study section on the detail page. '
                'Stats: [{"v": "500k+", "l": "downloads"}, ...] — shown on cards and the case-study hero.'
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
class ExperienceAdmin(TranslationAdmin, UnfoldModelAdmin):
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


@admin.register(TeamMember)
class TeamMemberAdmin(TranslationAdmin, UnfoldModelAdmin):
    list_per_page = 20
    list_display = ('thumbnail', 'name', 'role', 'years_experience', 'order', 'is_visible')
    list_display_links = ('thumbnail', 'name')
    list_editable = ('order', 'is_visible')
    list_filter = ('is_visible',)
    search_fields = ('name', 'role', 'bio')

    readonly_fields = ('real_prompt_help',)
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'role', 'photo', 'photo_real', 'years_experience',
                       'is_visible', 'order'),
            'description': (
                "<b>Photo</b> — anime portret (saytda ko'rinadi). "
                "<b>Photo real</b> — realistik portret: modal'da anime rasm "
                "bosilganda ochiladi (bo'sh = faqat anime)."
            ),
        }),
        ('Bio', {
            'fields': ('bio', 'quote', 'skills'),
            'description': 'Skills must be comma-separated.',
        }),
        ('Channels', {
            'fields': ('telegram_url', 'github_url', 'linkedin_url'),
            'classes': ('collapse',),
        }),
        ("📷 Real portret yasash (ixtiyoriy)", {
            'classes': ('collapse',),
            'fields': ('real_prompt_help',),
        }),
    )

    @admin.display(description='Realistik portret prompti')
    def real_prompt_help(self, obj=None):
        prompt = (
            "Transform this anime character portrait into a photorealistic "
            "photograph of a real person. Keep the EXACT same composition, framing, "
            "pose, hairstyle, clothing, colors and background from the reference — "
            "only convert the rendering style: natural skin texture, realistic eyes, "
            "soft studio lighting, DSLR portrait with shallow depth of field. The "
            "person must look like a plausible real human matching the character's "
            "apparent age, style and mood. No text, no watermark."
        )
        return render_prompt_box(
            prompt, 'team-real-prompt',
            "1) Promptni nusxalang. 2) nano_banana_pro (Higgsfield) yoki ChatGPT'da "
            "anime portretni referens qilib generatsiya qiling. 3) Natijani "
            "yuqoridagi 'Photo real' maydoniga yuklang."
        )

    def thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="48" height="48" '
                'style="border-radius:50%;object-fit:cover;'
                'border:1px solid rgba(255,255,255,.12);" />',
                obj.photo.url,
            )
        return format_html(
            '<div style="width:48px;height:48px;border-radius:50%;'
            'background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);'
            'display:flex;align-items:center;justify-content:center;'
            'font-family:Fraunces,serif;font-style:italic;font-size:18px;">{}</div>',
            obj.initials,
        )
    thumbnail.short_description = ''


# Anime cover generatsiya prompti — admin'da nusxalanadi (nano_banana_pro / ChatGPT).
# Universal: sahna-tavsifsiz, faqat "uslubni anime qil, kompozitsiyani saqla".
ANIME_COVER_PROMPT = (
    "Transform this photograph into a hand-painted Studio Ghibli / Makoto Shinkai "
    "anime illustration. It must look UNMISTAKABLY like a 2D anime cel painting, NOT "
    "a photo: flat cel-shaded coloring, bold clean ink outlines, simplified painterly "
    "anime faces, soft watercolor gradient skies and backgrounds, hand-drawn scenery, "
    "saturated storybook colors, visible brush texture. Preserve the EXACT same "
    "composition, framing, number of people, their poses, clothing and the setting "
    "from the reference — only convert the rendering style to anime. Anime movie "
    "poster look. No text, no watermark."
)


def render_prompt_box(prompt, box_id, intro):
    """Admin uchun: prompt matni + '📋 Nusxa olish' tugmasi (readonly ko'rinish)."""
    from django.utils.html import escape
    return mark_safe(
        '<p style="margin:0 0 8px;color:var(--font-subtle-color,#888);font-size:13px;">'
        + escape(intro) + '</p>'
        '<textarea readonly id="' + box_id + '" onclick="this.select();" '
        'style="width:100%;max-width:640px;min-height:150px;font-family:monospace;'
        'font-size:12px;line-height:1.5;padding:10px;border:1px solid rgba(128,128,128,.35);'
        'border-radius:6px;resize:vertical;background:rgba(128,128,128,.06);">'
        + escape(prompt) + '</textarea><br>'
        '<button type="button" onclick="'
        "var t=document.getElementById('" + box_id + "');t.select();"
        "if(navigator.clipboard){navigator.clipboard.writeText(t.value);}"
        "else{document.execCommand('copy');}"
        "var b=this;b.textContent='Nusxa olindi \\u2713';"
        "setTimeout(function(){b.textContent='\\ud83d\\udccb Promptni nusxalash';},1600);"
        '" style="margin-top:8px;padding:7px 16px;cursor:pointer;border-radius:6px;'
        'border:1px solid rgba(128,128,128,.4);background:transparent;font-size:13px;">'
        '\U0001f4cb Promptni nusxalash</button>'
    )


@admin.register(GalleryImage)
class GalleryImageAdmin(TranslationAdmin, UnfoldModelAdmin):
    list_per_page = 20
    list_display = ('preview', 'hint', 'dimensions', 'has_cover', 'is_visible', 'order')
    list_editable = ('is_visible', 'order')
    list_filter = ('is_visible',)
    search_fields = ('hint',)
    readonly_fields = ('preview', 'anime_prompt_help', 'width', 'height')
    fieldsets = (
        (None, {
            'fields': ('image', 'cover', 'preview', 'hint', 'is_visible', 'order'),
            'description': (
                "Ikki rasm: <b>Image</b> — asosiy (real) rasm, bosilganda ochiladi. "
                "<b>Cover</b> — devorda ko'rinadigan anime versiya (bo'sh bo'lsa "
                "asosiy rasmning o'zi devorda ko'rinadi va bosilganda kattalashadi)."
            ),
        }),
        ("🎨 Anime cover yasash (ixtiyoriy)", {
            'classes': ('collapse',),
            'fields': ('anime_prompt_help',),
        }),
    )

    @admin.display(description='Anime cover prompti')
    def anime_prompt_help(self, obj=None):
        return render_prompt_box(
            ANIME_COVER_PROMPT, 'gallery-anime-prompt',
            "1) Promptni nusxalang. 2) nano_banana_pro (Higgsfield) yoki ChatGPT'da "
            "shu rasmni referens qilib generatsiya qiling. 3) Natijani yuqoridagi "
            "'Cover' maydoniga yuklang. (Cover'siz ham devor ishlaydi — asosiy rasm ko'rinadi.)"
        )

    @admin.display(description='Rasm')
    def preview(self, obj):
        if not obj.image:
            return '—'
        if obj.cover:
            return format_html(
                '<span style="display:inline-flex;gap:6px;align-items:center;">'
                '<img src="{}" style="height:56px;border-radius:4px;" loading="lazy" title="cover (devorda)">'
                '<img src="{}" style="height:44px;border-radius:4px;opacity:.7;" loading="lazy" title="asosiy (lightbox)">'
                '</span>',
                obj.cover.url, obj.image.url,
            )
        return format_html(
            '<img src="{}" style="height:56px;border-radius:4px;" loading="lazy">',
            obj.image.url,
        )

    @admin.display(description='Cover', boolean=True)
    def has_cover(self, obj):
        return bool(obj.cover)

    @admin.display(description='O\'lcham')
    def dimensions(self, obj):
        return f'{obj.width}×{obj.height}' if obj.width else '—'
