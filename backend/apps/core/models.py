from django.db import models
from django.core.exceptions import ValidationError


class SiteSettings(models.Model):
    """
    Singleton model for global site configuration.
    Managed via Django admin — only one instance should exist.
    """

    # Meta fields
    site_title = models.CharField(
        max_length=255,
        default="JaysonKhan | Portfolio",
        help_text="Site title for <title> tag and branding"
    )
    site_tagline = models.CharField(
        max_length=500,
        default="Senior Python Backend Architect & Full-stack Developer.",
        help_text="Brief site description"
    )
    favicon = models.ImageField(
        upload_to='branding/',
        blank=True,
        null=True,
        help_text="Favicon (appears in browser tab)"
    )
    logo = models.ImageField(
        upload_to='branding/',
        blank=True,
        null=True,
        help_text="Site logo (optional, for future use)"
    )

    # SEO fields
    meta_description = models.TextField(
        max_length=160,
        default="Senior Python Backend Architect specializing in Django, PostgreSQL, and Clean Architecture. Available for freelance and full-time work.",
        help_text="Google search result description (max 160 characters)"
    )
    meta_keywords = models.CharField(
        max_length=255,
        default="Python, Django, PostgreSQL, Backend Developer, Software Architect, Portfolio",
        help_text="Comma-separated keywords for SEO"
    )
    og_image = models.ImageField(
        upload_to='seo/',
        blank=True,
        null=True,
        help_text="Open Graph image (Facebook, LinkedIn, Telegram preview)"
    )
    og_url = models.URLField(
        default="https://jaysonkhan.com",
        help_text="Open Graph URL"
    )

    # Hero section
    hero_title = models.CharField(
        max_length=255,
        default="I build high-performance backend systems.",
        help_text="Main hero section heading"
    )
    hero_subtitle = models.TextField(
        max_length=500,
        default="Senior Python Backend Architect specializing in Django, PostgreSQL, and Clean Architecture.",
        help_text="Hero section subheading"
    )
    hero_image = models.ImageField(
        upload_to='hero/',
        blank=True,
        null=True,
        help_text="Hero section image"
    )
    hero_availability_badge = models.CharField(
        max_length=100,
        default="Available for work",
        help_text="Badge text above hero title"
    )

    # About section
    about_title = models.CharField(
        max_length=255,
        default="About Me",
        help_text="About section heading"
    )
    about_description = models.TextField(
        default="Men 5+ yillik tajribaga ega Python backend arxitektiman. Django, FastAPI, PostgreSQL, "
                "Redis va Docker bilan professional darajada ishlayman. Clean Architecture va SOLID "
                "tamoyillariga amal qilgan holda yuqori samarali backend tizimlarni loyihalayman.",
        help_text="About section content"
    )
    about_image = models.ImageField(
        upload_to='about/',
        blank=True,
        null=True,
        help_text="About section image"
    )

    # Resume/CV
    resume_file = models.FileField(
        upload_to='cv/',
        blank=True,
        null=True,
        help_text="CV/Resume PDF for download"
    )
    resume_button_text = models.CharField(
        max_length=50,
        default="Download CV",
        help_text="Text for resume download button"
    )

    # Contact & Footer
    email = models.EmailField(
        default="jayson@jaysonkhan.com",
        help_text="Primary contact email"
    )
    footer_text = models.CharField(
        max_length=255,
        default="© 2026 JaysonKhan. All rights reserved.",
        help_text="Footer copyright text"
    )

    # Social links
    github_url = models.URLField(
        default="https://github.com/jaysonkhan",
        blank=True,
        help_text="GitHub profile URL"
    )
    linkedin_url = models.URLField(
        default="https://linkedin.com/in/jaysonkhan",
        blank=True,
        help_text="LinkedIn profile URL"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return f"Site Configuration"

    def save(self, *args, **kwargs):
        """Enforce singleton pattern — only one instance allowed."""
        if self.pk is None and SiteSettings.objects.exists():
            raise ValidationError("Only one SiteSettings instance is allowed. Edit the existing one.")
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Get or create the singleton instance with defaults.
        Safe fallback if DB is empty.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
