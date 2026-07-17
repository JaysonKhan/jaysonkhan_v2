from core.utils import sanitize_rich_text
from django.db import models
from django.utils.html import strip_tags
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
    stats = models.JSONField(
        blank=True, default=list,
        help_text=(
            "Key metrics for cards/case-study hero — list of {\"v\": \"500k+\", \"l\": \"downloads\"} "
            "objects (max 3 shown)"
        )
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

    @property
    def kind(self):
        """Project kind for the XIVA INK KindBadge: 'bot' | 'mobile' | 'web'."""
        if self.is_bot:
            return 'bot'
        if self.app_store_url or self.play_store_url:
            return 'mobile'
        return 'web'

    @property
    def kind_label(self):
        return {'web': 'WEB', 'bot': 'TG BOT', 'mobile': 'MOBILE'}[self.kind]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        for lang in ('xo', 'uz', 'ru', 'en'):
            field = 'description_rich_' + lang
            val = getattr(self, field, None)
            if val:
                setattr(self, field, sanitize_rich_text(val))
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


class GalleryImage(models.Model):
    """Bosh sahifa pastidagi 'gallery wall' kadri (footer tepasida).

    Rasmlar admin orqali yuklanadi; o'lchamlar saqlanadi (layout hech
    sakramasin — justified-flex `--ar` ni serverdan oladi). `hint` —
    hover'da chiqadigan izoh (modeltranslation: 4 til).
    """

    image = models.ImageField(
        upload_to='gallery/',
        help_text="Asosiy (original) rasm — lightbox'da ochiladi",
    )
    cover = models.ImageField(
        upload_to='gallery/covers/', blank=True, null=True,
        help_text="Devorda ko'rinadigan anime/ghibli cover (bo'sh = original ko'rinadi)",
    )
    hint = models.CharField(
        max_length=200,
        help_text="Hover'da chiqadigan qisqa izoh (4 tilda)",
    )
    width = models.PositiveIntegerField(default=0, editable=False)
    height = models.PositiveIntegerField(default=0, editable=False)
    cover_width = models.PositiveIntegerField(default=0, editable=False)
    cover_height = models.PositiveIntegerField(default=0, editable=False)
    is_visible = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Lower = displayed first")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Gallery image'
        verbose_name_plural = 'Gallery images'

    def __str__(self):
        return self.hint or f'Gallery #{self.pk}'

    def save(self, *args, **kwargs):
        # O'lchamlar saqlangan holda keladi (har renderda faylga tegmaslik uchun);
        # fayl ALMASHTIRILSA qayta o'qiymiz — eski --ar bilan layout buzilmasin
        old = {}
        if self.pk:
            old = (
                type(self)._default_manager.filter(pk=self.pk)
                .values('image', 'cover')
                .first()
                or {}
            )
        if self.image and (
            not self.width or not self.height or self.image.name != old.get('image')
        ):
            try:
                self.width = self.image.width
                self.height = self.image.height
            except Exception:
                pass
        if self.cover:
            if (
                not self.cover_width
                or not self.cover_height
                or self.cover.name != old.get('cover')
            ):
                try:
                    self.cover_width = self.cover.width
                    self.cover_height = self.cover.height
                except Exception:
                    pass
        else:
            # cover olib tashlangan — eski o'lchamlar qolib ketmasin
            self.cover_width = 0
            self.cover_height = 0
        super().save(*args, **kwargs)

    @property
    def aspect_css(self) -> str:
        """CSS uchun lokalizatsiyasiz aspect (`--ar`) — '1,5' emas, '1.5'."""
        if self.width and self.height:
            return f'{self.width / self.height:.4f}'
        return '1.5'

    @property
    def display_url(self) -> str:
        """Devorda ko'rinadigan rasm: cover bo'lsa cover, bo'lmasa original."""
        return self.cover.url if self.cover else self.image.url

    @property
    def display_aspect_css(self) -> str:
        """Devor layout uchun ko'rinadigan rasmning aspekti."""
        if self.cover and self.cover_width and self.cover_height:
            return f'{self.cover_width / self.cover_height:.4f}'
        return self.aspect_css

    @property
    def display_width(self):
        return self.cover_width if (self.cover and self.cover_width) else self.width

    @property
    def display_height(self):
        return self.cover_height if (self.cover and self.cover_height) else self.height
