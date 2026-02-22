from django.db import models
from django.utils.text import slugify


class Skill(models.Model):
    CATEGORY_CHOICES = [
    ('mobile', 'Mobile'),
    ('architecture', 'Architecture'),
    ('backend', 'Backend & Networking'),
    ('database', 'Databases'),
    ('security', 'Security'),
    ('performance', 'Performance'),
    ('media', 'Media & Streaming'),
    ('devops', 'DevOps & Tools'),
    ('uiux', 'UI/UX'),
    ]

    name = models.CharField(max_length=100)
    level = models.IntegerField(help_text="Skill level out of 100", default=80)
    icon = models.CharField(
        max_length=50, help_text="Tailwind or FontAwesome icon class", blank=True
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='other',
        help_text="Skill category for grouped display"
    )
    order = models.IntegerField(default=0, help_text="Display order within category")
    show_in_hero = models.BooleanField(
        default=False,
        help_text="Show this skill icon in the hero section orbit animation"
    )

    class Meta:
        ordering = ['category', 'order', 'name']

    def __str__(self):
        return self.name


class ProjectScreenshot(models.Model):
    project = models.ForeignKey(
        'Project', on_delete=models.CASCADE, related_name='screenshots'
    )
    image = models.ImageField(upload_to='projects/screenshots/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project.title} — screenshot {self.order}"


class Project(models.Model):
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('cross', 'Cross-platform (Android & iOS)'),
        ('web', 'Web'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(
        max_length=300, blank=True,
        help_text="One-liner for project cards (falls back to truncated description)"
    )
    image = models.ImageField(upload_to='projects/', blank=True, null=True)

    # Mobile-specific fields
    platform = models.CharField(
        max_length=10, choices=PLATFORM_CHOICES, default='cross',
        help_text="Target platform"
    )
    app_store_url = models.URLField(blank=True, help_text="Apple App Store link")
    play_store_url = models.URLField(blank=True, help_text="Google Play Store link")
    is_featured = models.BooleanField(
        default=False, help_text="Show on homepage featured section"
    )

    # Existing fields preserved
    technologies = models.ManyToManyField(Skill, related_name='projects', blank=True)
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_card_description(self):
        """Short description for cards."""
        return self.short_description or self.description[:200]

    def __str__(self):
        return self.title


class Experience(models.Model):
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    description = models.TextField()
    company_logo = models.ImageField(
        upload_to='experience/', blank=True, null=True,
        help_text="Company logo (optional, 128x128 recommended)"
    )
    company_url = models.URLField(blank=True, help_text="Company website URL")
    location = models.CharField(max_length=100, blank=True, help_text="e.g. Tashkent, Uzbekistan")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.position} at {self.company}"
