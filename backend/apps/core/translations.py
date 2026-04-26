"""Modeltranslation registrations for SiteSettings.

Each translatable field becomes one column per language in core_sitesettings:
  field           — proxy that reads the active language column
  field_xo, field_uz, field_ru, field_en — actual storage columns

Default `xo` (Khorezm) is the canonical column. Existing values are migrated
into `field_xo` automatically by the auto-generated migration.
"""
from modeltranslation.translator import register, TranslationOptions
from .models import SiteSettings, Asset


@register(SiteSettings)
class SiteSettingsTranslation(TranslationOptions):
    fields = (
        # ── Branding ────────────────────────────────────────────────────────
        'site_title',
        'site_tagline',

        # ── SEO ─────────────────────────────────────────────────────────────
        'meta_description',
        'meta_keywords',

        # ── Navigation ──────────────────────────────────────────────────────
        'nav_cta_text',

        # ── Hero ────────────────────────────────────────────────────────────
        'hero_title',
        'hero_subtitle',

        # ── About + Stats ───────────────────────────────────────────────────
        'about_title',
        'about_description',
        'stat_1_label', 'stat_2_label', 'stat_3_label', 'stat_4_label',

        # ── Section headings ────────────────────────────────────────────────
        'featured_projects_title',

        # ── Page titles ─────────────────────────────────────────────────────
        'projects_page_title', 'projects_page_subtitle',
        'blog_page_title', 'blog_page_subtitle',
        'contact_page_title', 'contact_page_subtitle',
        'resume_button_text',

        # ── Footer ──────────────────────────────────────────────────────────
        'footer_description',
        'footer_text',

        # ── Editorial v3 (60+ fields) ───────────────────────────────────────
        'hero_eyebrow',
        'brand_tagline',
        'manifesto_eyebrow', 'manifesto_title', 'manifesto_label',
        'metrics_eyebrow', 'metrics_title', 'metrics_description',
        'process_eyebrow', 'process_title',
        'cta_eyebrow', 'cta_title_pre', 'cta_title_em', 'cta_description',
        'cta_button_text', 'cta_response_label',
        'contact_form_label', 'contact_form_title',
        'contact_availability_status', 'contact_availability_note',
        'team_hero_eyebrow', 'team_hero_headline', 'team_intro',
        'team_values_eyebrow', 'team_values_title', 'team_values_intro',
        'about_section_eyebrow',
        'footer_cta_eyebrow', 'footer_cta_headline',
        'error_404_headline', 'error_404_description',
        'error_500_headline', 'error_500_description',
        'error_unavailable_headline', 'error_unavailable_description',
        'availability_badge',

        # ── JSON list fields (translated as a whole list per language) ──────
        'ticker_items',
        'manifesto_principles',
        'process_steps',
        'team_values',
        'footer_practice_items',
    )


@register(Asset)
class AssetTranslation(TranslationOptions):
    fields = ('alt_text', 'name')
