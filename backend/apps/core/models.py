from django.db import models
from django.core.exceptions import ValidationError


class SiteSettings(models.Model):
    """
    Singleton model — all dynamic site configuration lives here.
    One instance, managed via Django admin. Access via SiteSettings.load().
    Cache invalidation handled by SiteSettingsService.
    """

    # ── Branding ──────────────────────────────────────────────────────────────
    site_title = models.CharField(
        max_length=255, default="JaysonKhan | Portfolio",
        help_text="Full site name — used in <title> tag and nav logo"
    )
    site_author = models.CharField(
        max_length=100, default="JaysonKhan",
        help_text="Author name (used in blog byline and structured data)"
    )
    site_author_initials = models.CharField(
        max_length=5, default="JK",
        help_text="2–3 letter initials for avatar badge"
    )
    site_tagline = models.CharField(
        max_length=500,
        default="Senior Python Backend Architect & Full-stack Developer.",
        help_text="One-liner description — shown in footer"
    )
    favicon = models.ImageField(
        upload_to='branding/', blank=True, null=True,
        help_text="Favicon (ICO, PNG 32×32 or 64×64)"
    )
    logo = models.ImageField(
        upload_to='branding/', blank=True, null=True,
        help_text="Site logo — future navbar use"
    )

    # ── SEO / Meta ────────────────────────────────────────────────────────────
    meta_description = models.TextField(
        max_length=160,
        default="Senior Python Backend Architect specializing in Django, "
                "PostgreSQL, and Clean Architecture. Available for freelance and full-time work.",
        help_text="Google snippet description (max 160 chars)"
    )
    meta_keywords = models.CharField(
        max_length=255,
        default="Python, Django, PostgreSQL, Backend Developer, Software Architect, Portfolio",
        help_text="Comma-separated SEO keywords"
    )
    og_image = models.ImageField(
        upload_to='seo/', blank=True, null=True,
        help_text="Open Graph preview image (1200×630 px recommended)"
    )
    og_url = models.URLField(
        default="https://jaysonkhan.com",
        help_text="Canonical site URL for Open Graph"
    )
    twitter_handle = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Twitter/X handle without @ — for twitter:site tag"
    )

    # ── Navigation ────────────────────────────────────────────────────────────
    nav_cta_text = models.CharField(
        max_length=50, default="Hire Me",
        help_text="Navigation CTA button label"
    )
    nav_cta_url = models.CharField(
        max_length=200, default="/contact/",
        help_text="Navigation CTA button URL (relative or absolute)"
    )

    # ── Hero Section ──────────────────────────────────────────────────────────
    hero_availability_badge = models.CharField(
        max_length=100, default="Available for work",
        help_text="Small badge text above the hero headline"
    )
    hero_title = models.CharField(
        max_length=255, default="I build high-performance backend systems.",
        help_text="Main hero headline"
    )
    hero_subtitle = models.TextField(
        max_length=500,
        default="Senior Python Backend Architect specializing in Django, "
                "PostgreSQL, and Clean Architecture.",
        help_text="Hero sub-heading paragraph"
    )
    hero_image = models.ImageField(
        upload_to='hero/', blank=True, null=True,
        help_text="Hero section portrait/image"
    )
    hero_primary_cta_text = models.CharField(
        max_length=50, default="View Projects",
        help_text="Primary CTA button text in hero"
    )
    hero_primary_cta_url = models.CharField(
        max_length=200, default="/projects/",
        help_text="Primary CTA button URL"
    )
    hero_secondary_cta_text = models.CharField(
        max_length=50, default="Contact Me",
        help_text="Secondary CTA button text in hero"
    )
    hero_secondary_cta_url = models.CharField(
        max_length=200, default="/contact/",
        help_text="Secondary CTA button URL"
    )

    # ── About Section ─────────────────────────────────────────────────────────
    about_title = models.CharField(
        max_length=255, default="About",
        help_text="About section heading (template appends 'Me' with gradient)"
    )
    about_description = models.TextField(
        default="Men 5+ yillik tajribaga ega Python backend arxitektiman. "
                "Django, FastAPI, PostgreSQL, Redis va Docker bilan professional "
                "darajada ishlayman. Clean Architecture va SOLID tamoyillariga "
                "amal qilgan holda yuqori samarali backend tizimlarni loyihalayman.",
        help_text="About section body text"
    )
    about_image = models.ImageField(
        upload_to='about/', blank=True, null=True,
        help_text="About section portrait/image"
    )

    # ── Skills Section ────────────────────────────────────────────────────────
    skills_section_title = models.CharField(
        max_length=100, default="My Expertise",
        help_text="Skills section heading"
    )

    # ── Featured Projects Section ─────────────────────────────────────────────
    featured_projects_title = models.CharField(
        max_length=100, default="Featured Projects",
        help_text="Featured projects section heading"
    )
    featured_projects_subtitle = models.CharField(
        max_length=255, default="Some of my best architectural work.",
        help_text="Featured projects section sub-heading"
    )

    # ── Latest Blog Section ───────────────────────────────────────────────────
    latest_blog_title = models.CharField(
        max_length=100, default="Latest from the Blog",
        help_text="Latest blog section heading on homepage"
    )

    # ── Projects Page ─────────────────────────────────────────────────────────
    projects_page_title = models.CharField(
        max_length=100, default="Portfolio Projects",
        help_text="Projects page <h1> heading"
    )
    projects_page_subtitle = models.CharField(
        max_length=255,
        default="A detailed look at the systems and applications I've architected and implemented.",
        help_text="Projects page sub-heading"
    )

    # ── Blog Page ─────────────────────────────────────────────────────────────
    blog_page_title = models.CharField(
        max_length=100, default="The Blog",
        help_text="Blog list page <h1> heading"
    )
    blog_page_subtitle = models.CharField(
        max_length=255,
        default="Insights on software architecture, backend engineering, and the future of web development.",
        help_text="Blog list page sub-heading"
    )

    # ── Contact Page ──────────────────────────────────────────────────────────
    contact_page_title = models.CharField(
        max_length=100, default="Get in touch",
        help_text="Contact page <h1> heading"
    )
    contact_page_subtitle = models.CharField(
        max_length=500,
        default="Have a project in mind or just want to chat architectural patterns? Drop me a message.",
        help_text="Contact page intro paragraph"
    )
    contact_email_label = models.CharField(
        max_length=50, default="Email",
        help_text="Label for email contact block"
    )
    contact_linkedin_label = models.CharField(
        max_length=50, default="LinkedIn",
        help_text="Label for LinkedIn contact block"
    )

    # ── Resume / CV ───────────────────────────────────────────────────────────
    resume_file = models.FileField(
        upload_to='cv/', blank=True, null=True,
        help_text="CV / Resume PDF for download"
    )
    resume_button_text = models.CharField(
        max_length=50, default="Download CV",
        help_text="Resume download button label"
    )

    # ── Contact Info & Socials ────────────────────────────────────────────────
    email = models.EmailField(
        default="jayson@jaysonkhan.com",
        help_text="Primary contact email — shown in footer and contact page"
    )
    github_url = models.URLField(
        default="https://github.com/jaysonkhan", blank=True,
        help_text="GitHub profile URL"
    )
    linkedin_url = models.URLField(
        default="https://linkedin.com/in/jaysonkhan", blank=True,
        help_text="LinkedIn profile URL"
    )
    twitter_url = models.URLField(
        blank=True, default="",
        help_text="Twitter/X profile URL (optional)"
    )
    telegram_url = models.URLField(
        blank=True, default="",
        help_text="Telegram profile URL (optional)"
    )

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_text = models.CharField(
        max_length=255, default="© 2026 JaysonKhan. All rights reserved.",
        help_text="Footer copyright line"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        if self.pk is None and SiteSettings.objects.exists():
            raise ValidationError(
                "Only one SiteSettings instance is allowed. Edit the existing record."
            )
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return singleton, creating with defaults if absent."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
