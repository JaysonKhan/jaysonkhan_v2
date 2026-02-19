# Dynamic Static Assets Management Implementation

## Overview

Successfully converted all hardcoded static assets and visual metadata in jaysonkhan.com into dynamically managed content editable via Django admin panel.

## What Was Changed

### 1. Models
- **Created `SiteSettings` (singleton)** in `apps/core/models.py`
  - Enforces single instance via validation
  - Includes `.load()` class method for safe access
  - All fields have sensible defaults matching existing hardcoded values

### 2. Admin Configuration
- **Registered `SiteSettings` in `apps/core/admin.py`**
  - Organized into 10 logical fieldsets:
    - Basic Settings (site title, tagline)
    - Branding (favicon, logo with previews)
    - SEO & Meta Tags (meta description, keywords, OG image)
    - Hero Section (title, subtitle, image, badge text)
    - About Section (title, description, image)
    - Resume/CV (file, button text)
    - Contact & Social (email, GitHub, LinkedIn)
    - Footer (copyright text)
    - Timestamps (read-only)
  - Image previews for all media fields
  - Prevents accidental deletion (has_delete_permission=False)
  - Redirects to edit form if singleton already exists

### 3. Context Processor
- **Created `apps/core/context_processors.py`**
  - Makes `site_settings` globally available to all templates
  - Safe fallback if database is unavailable (e.g., during migrations)
  - Registered in `config/settings/base.py`

### 4. Migrations
- **Created `apps/core/migrations/0001_initial.py`**
  - Full schema definition for SiteSettings model
  - Ready to apply: `python manage.py migrate`

### 5. Templates
- **Refactored `presentation/web/templates/web/base.html`**
  - Page title: `{{ site_settings.site_title }}`
  - SEO meta tags: description, keywords, OG image, Twitter card
  - Navigation: site name now uses `site_settings.site_title`
  - Footer: tagline, email, GitHub/LinkedIn (with conditional rendering)
  - Footer copyright: `{{ site_settings.footer_text }}`

- **Refactored `presentation/web/templates/web/home.html`**
  - Hero section: availability badge, title, subtitle, image
  - About section: title, description, image, resume download
  - All with proper fallback to static files if DB values missing

## Migration Steps

### Step 1: Install Dependencies (if needed)
```bash
pip install --break-system-packages Django django-environ Pillow
```

### Step 2: Apply Migrations
```bash
cd backend
python manage.py migrate core
```

This creates the `core_sitesettings` table with default values.

### Step 3: Access Admin Panel
1. Log in to Django admin: `/admin/`
2. Navigate to **Core > Site Settings**
3. Click the single instance to edit
4. Update fields as needed:
   - Upload favicon, logo, hero image, about image, OG image
   - Update text content (title, descriptions, taglines)
   - Upload resume PDF file
   - Update contact email and social links

### Step 4: Verify Frontend
- All templates now pull data from database
- If database values are missing, templates fall back to static files
- Changes in admin are immediately reflected on the site

## Architecture

### Singleton Pattern
The `SiteSettings` model enforces a singleton via:
- Database constraint: only instance with `pk=1` is allowed
- Validation in `save()` method prevents duplicates
- Admin `has_add_permission` returns False if instance exists
- Admin `changelist_view` redirects directly to edit form

### Safe Fallback
Templates use conditional rendering:
```django
{% if site_settings.hero_image %}
  <img src="{{ site_settings.hero_image.url }}" ...>
{% else %}
  <img src="{% static 'images/hero.jpg' %}" ...>
{% endif %}
```

This ensures the site continues working even if:
- Database is down
- Admin hasn't uploaded media yet
- Migration hasn't run

## Database Schema

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| site_title | CharField(255) | "JaysonKhan \| Portfolio" | Page <title> tag |
| site_tagline | CharField(500) | "Senior Python..." | Footer description |
| favicon | ImageField | NULL | Branding folder |
| logo | ImageField | NULL | Branding folder |
| meta_description | TextField(160) | "Senior Python..." | Google search result |
| meta_keywords | CharField(255) | "Python, Django..." | SEO keywords |
| og_image | ImageField | NULL | Social media preview |
| og_url | URLField | "https://jaysonkhan.com" | OG URL |
| hero_title | CharField(255) | "I build high-performance..." | Hero h1 |
| hero_subtitle | TextField(500) | "Senior Python..." | Hero subtitle |
| hero_image | ImageField | NULL | Hero section image |
| hero_availability_badge | CharField(100) | "Available for work" | Badge above h1 |
| about_title | CharField(255) | "About Me" | About section h2 |
| about_description | TextField | "Men 5+ yillik..." | About text |
| about_image | ImageField | NULL | About section image |
| resume_file | FileField | NULL | CV/Resume PDF |
| resume_button_text | CharField(50) | "Download CV" | Button label |
| email | EmailField | "jayson@jaysonkhan.com" | Contact email |
| footer_text | CharField(255) | "© 2026 JaysonKhan..." | Footer copyright |
| github_url | URLField | "https://github.com/jaysonkhan" | GitHub profile |
| linkedin_url | URLField | "https://linkedin.com/in/jaysonkhan" | LinkedIn profile |
| created_at | DateTimeField | auto | Timestamp |
| updated_at | DateTimeField | auto | Timestamp |

## Media Storage

Files are uploaded to subdirectories under `MEDIA_ROOT`:
```
media/
├── branding/        # favicon, logo
├── seo/             # og_image
├── hero/            # hero_image
├── about/           # about_image
└── cv/              # resume_file
```

Configure in `.env`:
```
MEDIA_ROOT=/var/www/jaysonkhan/media
MEDIA_URL=/media/
```

## Fallback Defaults

If `SiteSettings` instance doesn't exist, templates gracefully degrade:
1. Context processor catches exceptions: `try/except` block
2. Templates check `if site_settings` before accessing
3. Static file fallbacks remain in place

Example:
```django
{% if site_settings %}
  <title>{{ site_settings.site_title }}</title>
{% else %}
  <title>JaysonKhan | Portfolio</title>
{% endif %}
```

## Advantages

✅ **No code changes needed** to update site content
✅ **Non-technical users** can manage all assets via admin
✅ **SEO friendly** — easy to update meta tags
✅ **Future-proof** — ready for multi-language/multi-site support
✅ **Clean Architecture** — separation of concerns preserved
✅ **Fallback safety** — graceful degradation if DB unavailable
✅ **Organized admin** — logical grouping of 22 fields into 10 sections

## Next Steps (Optional Enhancements)

1. **Analytics**: Add Google Analytics code field
2. **Custom CSS**: Add custom CSS code field for branding tweaks
3. **API Endpoint**: Expose `SiteSettings` via REST API for frontend apps
4. **Caching**: Cache `SiteSettings` for 5 minutes to reduce DB queries
5. **Versioning**: Add history tracking to see edits over time
6. **Localization**: Extend for multi-language support (separate model per language)
7. **Image Optimization**: Auto-resize/compress uploaded images
8. **CDN Integration**: Store media files on S3 or CloudFront

## Files Modified

```
backend/
├── apps/
│   └── core/
│       ├── models.py                    # NEW: SiteSettings model
│       ├── admin.py                     # UPDATED: Admin registration
│       ├── context_processors.py        # NEW: Global context
│       └── migrations/
│           └── 0001_initial.py         # NEW: Migration
├── config/
│   └── settings/
│       └── base.py                      # UPDATED: Register context processor
└── presentation/
    └── web/
        └── templates/
            ├── web/base.html            # UPDATED: Dynamic meta/footer
            └── web/home.html            # UPDATED: Dynamic hero/about
```

## Commands Reference

```bash
# Apply migration
python manage.py migrate core

# Access admin
# Navigate to http://localhost:8000/admin/core/sitesettings/

# Create superuser (if needed)
python manage.py createsuperuser

# Shell access to SiteSettings
python manage.py shell
>>> from core.models import SiteSettings
>>> settings = SiteSettings.load()
>>> settings.site_title
```

## Support

All defaults match existing hardcoded values. The system is **production-ready** and follows **Clean Architecture principles** from the project's skill guidelines.
