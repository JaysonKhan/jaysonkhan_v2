from django.db import models
from django.utils.text import slugify
from django.utils.html import strip_tags
from core.utils import sanitize_rich_text


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
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='mobile',
        help_text="Skill category for grouped display"
    )
    order = models.IntegerField(default=0, help_text="Display order within category")

    class Meta:
        ordering = ['category', 'order', 'name']

    def __str__(self):
        return self.name





class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description_rich = models.TextField(blank=True, null=True, help_text="Rich text description (HTML)")
    short_description = models.CharField(
        max_length=300, blank=True,
        help_text="One-liner for project cards (falls back to truncated description)"
    )
    image = models.ImageField(upload_to='projects/', blank=True, null=True)

    app_store_url = models.URLField(blank=True, help_text="Apple App Store link")
    play_store_url = models.URLField(blank=True, help_text="Google Play Store link")
    web_page_url = models.URLField(
        blank=True,
        help_text="Web page / live URL"
    )
    is_bot = models.BooleanField(
        default=False,
        help_text="Show in the Telegram Bot section"
    )
    is_featured = models.BooleanField(
        default=False, help_text="Show on homepage featured section"
    )
    is_visible = models.BooleanField(
        default=True,
        help_text=(
            "Show this project in the Apps section. "
            "Uncheck to hide it from the project list and detail page "
            "even when the Apps section is enabled."
        )
    )

    # Existing fields preserved
    technologies = models.ManyToManyField(Skill, related_name='projects', blank=True)
    github_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Case Study (optional structured fields) ──────────────────────
    case_study_challenge = models.TextField(
        blank=True, default='',
        help_text="Case Study — Challenge/Problem (leave empty to hide)"
    )
    case_study_solution = models.TextField(
        blank=True, default='',
        help_text="Case Study — Solution approach"
    )
    case_study_results = models.TextField(
        blank=True, default='',
        help_text="Case Study — Results/Outcomes"
    )

    class Meta:
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['is_visible', 'order', '-created_at'],
                         name='proj_visible_order'),
            models.Index(fields=['is_featured', 'is_visible'],
                         name='proj_featured'),
            models.Index(fields=['is_bot', 'is_visible'],
                         name='proj_bot'),
        ]

    @property
    def has_case_study(self):
        return bool(self.case_study_challenge or self.case_study_solution or self.case_study_results)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.description_rich:
            self.description_rich = sanitize_rich_text(self.description_rich)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('project_detail', kwargs={'slug': self.slug})

    def get_card_description(self):
        """Short description for cards."""
        rich_text_content = strip_tags(self.description_rich or '')
        return self.short_description or rich_text_content[:200]

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


class TeamMember(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=160, help_text="e.g. Founder · Lead Mobile")
    bio = models.TextField(help_text="2-4 sentences about the member")
    photo = models.ImageField(
        upload_to='team/', blank=True, null=True,
        help_text="Square portrait (recommended 800x800)"
    )
    quote = models.CharField(
        max_length=240, blank=True,
        help_text="Optional one-liner shown in the dossier modal"
    )
    skills = models.CharField(
        max_length=400, blank=True,
        help_text="Comma-separated, e.g. 'Flutter, Bloc, Architecture, iOS, Android'"
    )
    years_experience = models.PositiveIntegerField(
        default=0,
        help_text="Total years of experience (shown as '4y')"
    )
    telegram_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    is_visible = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Lower = displayed first")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Team member'
        verbose_name_plural = 'Team members'

    def __str__(self):
        return f"{self.name} — {self.role}"

    @property
    def initials(self):
        parts = self.name.strip().split()
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def skills_list(self):
        return [s.strip() for s in self.skills.split(',') if s.strip()]
