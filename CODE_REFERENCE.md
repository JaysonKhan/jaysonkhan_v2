# Code Reference — Dynamic Assets Implementation

## Quick Navigation

- [SiteSettings Model](#sitesettings-model)
- [Admin Configuration](#admin-configuration)
- [Context Processor](#context-processor)
- [Template Usage](#template-usage)
- [Settings Configuration](#settings-configuration)

---

## SiteSettings Model

**File:** `backend/apps/core/models.py`

### Key Features
- Singleton pattern (only one instance)
- 24 fields covering all site metadata
- `.load()` method for safe access
- Validation prevents duplicates
- Proper defaults matching existing hardcoded values

### Core Methods

```python
@classmethod
def load(cls):
    """Get or create the singleton instance with defaults."""
    obj, _ = cls.objects.get_or_create(pk=1)
    return obj
```

### Field Groups

```python
# Meta (2 fields)
site_title: CharField(255)
site_tagline: CharField(500)

# Branding (2 fields)
favicon: ImageField(upload_to='branding/')
logo: ImageField(upload_to='branding/')

# SEO (5 fields)
meta_description: TextField(160)
meta_keywords: CharField(255)
og_image: ImageField(upload_to='seo/')
og_url: URLField()

# Hero (4 fields)
hero_title: CharField(255)
hero_subtitle: TextField(500)
hero_image: ImageField(upload_to='hero/')
hero_availability_badge: CharField(100)

# About (3 fields)
about_title: CharField(255)
about_description: TextField()
about_image: ImageField(upload_to='about/')

# Resume (2 fields)
resume_file: FileField(upload_to='cv/')
resume_button_text: CharField(50)

# Contact (3 fields)
email: EmailField()
github_url: URLField()
linkedin_url: URLField()

# Footer (1 field)
footer_text: CharField(255)

# Timestamps (2 fields)
created_at: DateTimeField(auto_now_add=True)
updated_at: DateTimeField(auto_now=True)
```

### Validation

```python
def save(self, *args, **kwargs):
    """Enforce singleton pattern — only one instance allowed."""
    if self.pk is None and SiteSettings.objects.exists():
        raise ValidationError("Only one SiteSettings instance is allowed.")
    super().save(*args, **kwargs)
```

---

## Admin Configuration

**File:** `backend/apps/core/admin.py`

### Registration

```python
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    # Configuration here
```

### Permission Controls

```python
def has_add_permission(self, request):
    """Prevent adding multiple instances"""
    return not SiteSettings.objects.exists()

def has_delete_permission(self, request, obj=None):
    """Prevent deletion of the singleton"""
    return False
```

### Fieldsets Organization

```python
fieldsets = (
    ('Basic Settings', {
        'fields': ('site_title', 'site_tagline'),
    }),
    ('Branding', {
        'fields': ('favicon', 'favicon_preview', 'logo', 'logo_preview'),
        'classes': ('collapse',),  # Collapsed by default
    }),
    # ... more fieldsets
)
```

### Read-only Fields

```python
readonly_fields = (
    'created_at',
    'updated_at',
    'favicon_preview',
    'logo_preview',
    'og_image_preview',
    'hero_image_preview',
    'about_image_preview',
    'resume_preview',
)
```

### Image Preview Methods

```python
def hero_image_preview(self, obj):
    if obj.hero_image:
        return format_html(
            '<img src="{}" width="300" height="auto" style="border-radius: 4px;" />',
            obj.hero_image.url
        )
    return "No hero image uploaded"
hero_image_preview.short_description = "Hero Image Preview"
```

### Auto-redirect to Edit Form

```python
def changelist_view(self, request, extra_context=None):
    """Redirect to edit view if singleton exists."""
    obj = SiteSettings.objects.first()
    if obj:
        from django.shortcuts import redirect
        return redirect(f'admin:core_sitesettings_change', obj.pk)
    return super().changelist_view(request, extra_context)
```

---

## Context Processor

**File:** `backend/apps/core/context_processors.py`

### Implementation

```python
def site_settings(request):
    """
    Inject SiteSettings into template context.
    Accessible as {{ site_settings }} in all templates.
    """
    try:
        settings = SiteSettings.load()
    except Exception:
        # Fallback if DB is unavailable
        settings = None

    return {
        'site_settings': settings,
    }
```

### Registration in Settings

**File:** `backend/config/settings/base.py`

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'presentation' / 'web' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_settings',  # ← Added this
            ],
        },
    },
]
```

---

## Template Usage

### Base Template: Meta Tags

**File:** `backend/presentation/web/templates/web/base.html`

```django
<title>{% block title %}{{ site_settings.site_title }}{% endblock %}</title>

<!-- SEO Meta Tags -->
<meta name="description" content="{{ site_settings.meta_description }}">
<meta name="keywords" content="{{ site_settings.meta_keywords }}">

<!-- Open Graph -->
<meta property="og:title" content="{{ site_settings.site_title }}">
<meta property="og:description" content="{{ site_settings.meta_description }}">
{% if site_settings.og_image %}
<meta property="og:image" content="{{ site_settings.og_image.url }}">
{% endif %}
<meta property="og:url" content="{{ site_settings.og_url }}">

<!-- Twitter Card -->
<meta name="twitter:title" content="{{ site_settings.site_title }}">
<meta name="twitter:description" content="{{ site_settings.meta_description }}">
{% if site_settings.og_image %}
<meta name="twitter:image" content="{{ site_settings.og_image.url }}">
{% endif %}
```

### Base Template: Navigation

```django
<a href="{% url 'home' %}" class="text-2xl font-bold">
    {{ site_settings.site_title|truncatewords:2 }}
</a>
```

### Base Template: Footer

```django
<h3 class="text-xl font-bold">
    {{ site_settings.site_title|truncatewords:2 }}
</h3>
<p class="text-slate-400">
    {{ site_settings.site_tagline }}
</p>

<p>Email: {{ site_settings.email }}</p>

{% if site_settings.github_url %}
<a href="{{ site_settings.github_url }}" target="_blank">GitHub</a>
{% endif %}

{% if site_settings.linkedin_url %}
<a href="{{ site_settings.linkedin_url }}" target="_blank">LinkedIn</a>
{% endif %}

<div class="text-center">
    {{ site_settings.footer_text }}
</div>
```

### Home Template: Hero Section

**File:** `backend/presentation/web/templates/web/home.html`

```django
<h2>{{ site_settings.hero_availability_badge }}</h2>
<h1>{{ site_settings.hero_title|safe }}</h1>
<p>{{ site_settings.hero_subtitle }}</p>

{% if site_settings.hero_image %}
<img src="{{ site_settings.hero_image.url }}" alt="...">
{% else %}
<img src="{% static 'images/hero.jpg' %}" alt="...">
{% endif %}
```

### Home Template: About Section

```django
<h2>{{ site_settings.about_title }} <span>Me</span></h2>
<p>{{ site_settings.about_description }}</p>

{% if site_settings.resume_file %}
<a href="{{ site_settings.resume_file.url }}" download>
    {{ site_settings.resume_button_text }}
</a>
{% else %}
<div>Resume not available</div>
{% endif %}

{% if site_settings.about_image %}
<img src="{{ site_settings.about_image.url }}" alt="...">
{% else %}
<img src="{% static 'images/about.jpg' %}" alt="...">
{% endif %}
```

---

## Settings Configuration

### Media Files Configuration

**File:** `backend/config/settings/base.py`

```python
# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = env('MEDIA_ROOT', default=str(BASE_DIR / 'media'))
```

### Static Files Configuration

```python
# Static files (CSS, JS, images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = env('STATIC_ROOT', default=str(BASE_DIR / 'staticfiles'))
```

### Environment Variables (.env)

```bash
# Media storage path
MEDIA_ROOT=/var/www/jaysonkhan/media

# Static files
STATIC_ROOT=/var/www/jaysonkhan/staticfiles
```

---

## Usage Examples

### In Python (Shell or Views)

```python
from core.models import SiteSettings

# Get singleton instance
settings = SiteSettings.load()

# Access fields
print(settings.site_title)
print(settings.email)
print(settings.hero_image.url)

# Update fields
settings.site_title = "New Title"
settings.email = "new@email.com"
settings.save()
```

### In Templates

```django
{# Always available globally #}
<title>{{ site_settings.site_title }}</title>

{# Conditional rendering #}
{% if site_settings.logo %}
  <img src="{{ site_settings.logo.url }}">
{% endif %}

{# Filters #}
{{ site_settings.site_title|truncatewords:2 }}

{# Safe HTML #}
{{ site_settings.hero_title|safe }}
```

### With Caching (Optional)

```python
from django.core.cache import cache
from core.models import SiteSettings

def get_site_settings():
    """Get cached SiteSettings or fetch from DB"""
    settings = cache.get('site_settings')
    if settings is None:
        settings = SiteSettings.load()
        cache.set('site_settings', settings, 60*5)  # Cache 5 minutes
    return settings
```

---

## Testing

### Unit Test Example

```python
from django.test import TestCase
from core.models import SiteSettings

class SiteSettingsTestCase(TestCase):
    def test_singleton_pattern(self):
        """Verify only one instance can exist"""
        settings1 = SiteSettings.load()
        settings2 = SiteSettings.load()

        self.assertEqual(settings1.pk, settings2.pk)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_defaults_exist(self):
        """Verify default values are set"""
        settings = SiteSettings.load()

        self.assertEqual(
            settings.site_title,
            "JaysonKhan | Portfolio"
        )
        self.assertEqual(
            settings.email,
            "jayson@jaysonkhan.com"
        )
```

### Template Test Example

```python
from django.test import Client

class TemplateTestCase(TestCase):
    def test_home_uses_site_settings(self):
        """Verify homepage uses dynamic site_settings"""
        response = self.client.get('/')

        self.assertContains(
            response,
            "JaysonKhan | Portfolio"
        )
```

---

## Debugging

### Check if SiteSettings Exists

```bash
python manage.py shell
>>> from core.models import SiteSettings
>>> SiteSettings.objects.all()
<QuerySet [<SiteSettings: Site Configuration>]>
```

### Check Database Query

```python
from django.db import connection

SiteSettings.load()
print(connection.queries[-1])  # Shows the SQL query
```

### Template Context Debugging

```django
{# In template #}
<pre>{{ site_settings }}</pre>
{# Shows all fields and values #}

{# Or check specific field #}
<pre>{{ site_settings.hero_title }}</pre>
```

---

## Common Pitfalls & Solutions

### ❌ Hardcoding URLs in templates
```django
{# Wrong #}
<img src="/static/images/hero.jpg">

{# Right #}
{% if site_settings.hero_image %}
  <img src="{{ site_settings.hero_image.url }}">
{% else %}
  <img src="{% static 'images/hero.jpg' %}">
{% endif %}
```

### ❌ Forgetting .url on ImageField
```django
{# Wrong #}
<img src="{{ site_settings.hero_image }}">

{# Right #}
<img src="{{ site_settings.hero_image.url }}">
```

### ❌ Not escaping HTML in hero_title
```django
{# Wrong #}
<h1>{{ site_settings.hero_title }}</h1>

{# Right (if HTML like <span> is needed) #}
<h1>{{ site_settings.hero_title|safe }}</h1>
```

### ❌ Forgetting context processor in settings
```python
# Wrong - forgot to add context processor
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.auth',
            # Missing: 'core.context_processors.site_settings'
        ],
    },
}]

# Right
TEMPLATES = [{
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.auth',
            'core.context_processors.site_settings',  # ✓ Added
        ],
    },
}]
```

---

## Performance Considerations

### Database Queries
- **1 query per request** (get SiteSettings instance)
- **Query time:** ~1-2ms typical
- **Cacheable:** Recommended 5-minute cache

### Caching Strategy

```python
# In context processor
def site_settings(request):
    settings = cache.get_or_set(
        'site_settings',
        SiteSettings.load,
        60 * 5  # 5 minutes
    )
    return {'site_settings': settings}
```

### Cache Invalidation

```python
# In SiteSettingsAdmin
def save_model(self, request, obj, form, change):
    super().save_model(request, obj, form, change)
    cache.delete('site_settings')  # Clear cache on update
```

---

## Migration Commands

```bash
# Create initial migration
python manage.py makemigrations core

# Apply migrations
python manage.py migrate core

# Show migration status
python manage.py showmigrations core

# Revert migration
python manage.py migrate core 0001
```

---

## File Structure Summary

```
backend/
├── apps/
│   └── core/
│       ├── models.py                    (SiteSettings model)
│       ├── admin.py                     (Admin configuration)
│       ├── context_processors.py        (Context processor)
│       ├── migrations/
│       │   └── 0001_initial.py         (Migration)
│       └── tests.py                     (Test cases)
├── config/
│   └── settings/
│       └── base.py                      (Registered context processor)
└── presentation/
    └── web/
        └── templates/
            ├── base.html                (Updated with dynamic content)
            └── home.html                (Updated with dynamic content)
```

---

**Last Updated:** February 19, 2026
**Version:** 1.0
**Status:** Production-ready
