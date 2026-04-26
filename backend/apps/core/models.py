import uuid

from django.core.cache import cache
from django.db import models
from django.core.exceptions import ValidationError


# ── Abstract Mixins ──────────────────────────────────────────────────────────────
# Each mixin groups related fields. They are abstract, so Django stores
# everything in a single `core_sitesettings` table — no migrations needed.


class BrandingMixin(models.Model):
    """Site identity — title, author, favicon, logo."""

    site_title = models.CharField(
        max_length=255, default="Jaysonkhan | VibeCoder · Build Studio",
        help_text="Full site name — used in the page title tag and nav logo"
    )
    site_author = models.CharField(
        max_length=100, default="Jahongir Kuziboev",
        help_text="Author name (used in blog byline and structured data)"
    )
    site_author_initials = models.CharField(
        max_length=5, default="JK",
        help_text="2–3 letter initials for avatar badge"
    )
    site_tagline = models.CharField(
        max_length=500,
        default="VibeCoder — shipping production web apps & Telegram bots via AI-augmented development.",
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

    class Meta:
        abstract = True


class SEOMixin(models.Model):
    """Search engine optimization and social sharing metadata."""

    meta_description = models.TextField(
        max_length=160,
        default="Jaysonkhan — VibeCoder shipping production web apps & "
                "Telegram bots via AI-augmented development. Build Studio · Tashkent.",
        help_text="Google snippet description (max 160 chars)"
    )
    meta_keywords = models.CharField(
        max_length=255,
        default="VibeCoder, Django, Python, Telegram bots, AI development, Claude Code, full stack, build studio, Tashkent",
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

    # ── Analytics ────────────────────────────────────────────────────────────
    google_analytics_id = models.CharField(
        max_length=20, blank=True, default="",
        help_text="GA4 Measurement ID, e.g. G-XXXXXXXXXX"
    )
    yandex_metrika_id = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Yandex Metrica counter ID (digits only)"
    )

    # ── Search Console Verification ──────────────────────────────────────────
    google_site_verification = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Google Search Console token (content= value of the meta tag)"
    )
    yandex_verification = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Yandex Webmaster verification token (content= value)"
    )
    bing_verification = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Bing Webmaster msvalidate.01 token"
    )

    class Meta:
        abstract = True


class NavigationMixin(models.Model):
    """Header navigation and CTA configuration."""

    logo_text = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Text next to logo (leave blank to use site_author)"
    )
    nav_cta_text = models.CharField(
        max_length=50, default="Hire Me",
        help_text="Navigation CTA button label"
    )
    nav_cta_url = models.CharField(
        max_length=200, default="/contact/",
        help_text="Navigation CTA button URL (relative or absolute)"
    )
    nav_links_json = models.JSONField(
        blank=True, default=list,
        help_text='Extra nav links as JSON list, e.g. [{"label":"Resume","url":"/resume/"}]. Leave empty for default nav.'
    )

    class Meta:
        abstract = True


class HeroMixin(models.Model):
    """Hero section — headline, subtitle, optional image. CTAs/typing/badge moved to EditorialContentMixin."""

    hero_title = models.CharField(
        max_length=255, default="I ship production web apps and Telegram bots.",
        help_text="Main hero headline (HTML allowed; leave blank to use v3 default)"
    )
    hero_subtitle = models.TextField(
        max_length=500,
        default="VibeCoder shipping production-grade web applications, Telegram bots, "
                "and AI-augmented systems. Built fast with Claude Code, built to last with Django.",
        help_text="Hero sub-heading paragraph"
    )
    hero_image = models.ImageField(
        upload_to='hero/', blank=True, null=True,
        help_text="Hero section portrait/image"
    )

    class Meta:
        abstract = True


class ContentSectionsMixin(models.Model):
    """Section headings, visibility flags, and page-level titles."""

    # ── About Section
    about_title = models.CharField(
        max_length=255, default="About",
        help_text="About section heading (template appends 'Me' with gradient)"
    )
    about_description = models.TextField(
        default="Full-stack VibeCoder with 3+ years shipping production systems. "
                "I build web apps with Django, Telegram bots with Aiogram, and "
                "design systems with Tailwind — all augmented by Claude Code and a "
                "sane workflow. Background in mobile (Flutter, Android, iOS), but the "
                "studio's center of gravity has moved to web + bots + AI.",
        help_text="About section body text"
    )
    about_image = models.ImageField(
        upload_to='about/', blank=True, null=True,
        help_text="About section portrait/image"
    )

    # ── Stats Bar
    stat_1_count = models.IntegerField(
        default=3,
        help_text="Stat 1 — numeric value for animated counter (e.g. 3)"
    )
    stat_1_suffix = models.CharField(
        max_length=10, default="+",
        help_text="Stat 1 — suffix appended to count (e.g. '+', 'M+', '%')"
    )
    stat_1_label = models.CharField(
        max_length=60, default="Years Experience",
        help_text="Stat 1 — label below the number"
    )
    stat_2_count = models.IntegerField(default=30)
    stat_2_suffix = models.CharField(max_length=10, default="+")
    stat_2_label = models.CharField(max_length=60, default="Apps Delivered")
    stat_3_count = models.IntegerField(default=1)
    stat_3_suffix = models.CharField(max_length=10, default="M+")
    stat_3_label = models.CharField(max_length=60, default="App Downloads")
    stat_4_count = models.IntegerField(default=100)
    stat_4_suffix = models.CharField(max_length=10, default="%")
    stat_4_label = models.CharField(max_length=60, default="Clean Architecture")

    # ── Section Headings
    featured_projects_title = models.CharField(
        max_length=100, default="Featured Apps",
        help_text="Featured projects section heading"
    )

    # ── Visibility
    apps_section_visible = models.BooleanField(
        default=True,
        help_text=(
            "Show/hide the entire Apps section (navigation link, footer link, "
            "homepage featured projects, and hero CTA). "
            "Turn OFF to temporarily hide this section across the whole site."
        )
    )

    # ── Page Titles
    projects_page_title = models.CharField(
        max_length=100, default="App Portfolio",
        help_text="Projects page <h1> heading"
    )
    projects_page_subtitle = models.CharField(
        max_length=255,
        default="A showcase of the mobile applications I've designed, developed, and shipped.",
        help_text="Projects page sub-heading"
    )
    blog_page_title = models.CharField(
        max_length=100, default="The Blog",
        help_text="Blog list page <h1> heading"
    )
    blog_page_subtitle = models.CharField(
        max_length=255,
        default="Notes on AI-augmented development, full-stack delivery, and shipping production systems that actually run.",
        help_text="Blog list page sub-heading"
    )
    contact_page_title = models.CharField(
        max_length=100, default="Get in touch",
        help_text="Contact page <h1> heading"
    )
    contact_page_subtitle = models.CharField(
        max_length=500,
        default="Building a web app, Telegram bot, or AI-augmented system? Let's ship it together.",
        help_text="Contact page intro paragraph"
    )
    resume_file = models.FileField(
        upload_to='cv/', blank=True, null=True,
        help_text="CV / Resume PDF for download"
    )
    resume_button_text = models.CharField(
        max_length=50, default="Download CV",
        help_text="Resume download button label"
    )

    class Meta:
        abstract = True


class ContactSocialsMixin(models.Model):
    """Contact info, social media links, and API keys."""

    email = models.EmailField(
        default="bettaxacker@gmail.com",
        help_text="Primary contact email — shown in footer and contact page"
    )
    phone = models.CharField(
        max_length=20, blank=True, default="",
        help_text="Phone number (optional)"
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

    class Meta:
        abstract = True


class TelegramMixin(models.Model):
    """Telegram bot integration — notifications, channel, custom emoji."""

    telegram_owner_id = models.BigIntegerField(
        null=True, blank=True,
        help_text="Telegram user ID of the site owner. Always receives notifications."
    )
    telegram_admin_group_id = models.BigIntegerField(
        null=True, blank=True,
        help_text="Telegram group/supergroup chat ID for admin notifications."
    )
    telegram_channel_id = models.BigIntegerField(
        null=True, blank=True,
        help_text=(
            "Telegram channel chat ID for publishing blog posts and projects. "
            "Numeric ID (e.g. -1001234567890). "
            "Changing this allows re-sharing content to the new channel."
        ),
    )
    admin_notify_new_users = models.BooleanField(
        default=True, help_text="Log new user registrations to admin group"
    )
    admin_notify_comments = models.BooleanField(
        default=True, help_text="Log new comments to admin group"
    )
    admin_notify_replies = models.BooleanField(
        default=True, help_text="Log comment replies to admin group"
    )
    admin_notify_reactions = models.BooleanField(
        default=True, help_text="Log reactions to admin group"
    )
    admin_notify_likes = models.BooleanField(
        default=True, help_text="Log likes/unlikes to admin group"
    )
    admin_notify_contacts = models.BooleanField(
        default=True, help_text="Log contact form submissions to admin group"
    )

    # ── Custom Emoji IDs (Bot API 9.4+)
    tg_emoji_read_more = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 📖 Batafsil button (e.g. 5368324170671202286)"
    )
    tg_emoji_google_play = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for ▶️ Google Play button"
    )
    tg_emoji_app_store = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🍎 App Store button"
    )
    tg_emoji_web = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🌐 Web button"
    )
    tg_emoji_bot = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🤖 Telegram Bot button"
    )
    tg_emoji_github = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 💻 GitHub button"
    )
    tg_emoji_comment = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 💬 Comment/reply buttons"
    )

    # ── Server Monitor Custom Emoji (premium stickers) ──
    tg_emoji_server = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🖥 Server/status headers"
    )
    tg_emoji_cpu = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🧠 CPU section"
    )
    tg_emoji_ram = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 💾 RAM section"
    )
    tg_emoji_disk = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 💿 Disk section"
    )
    tg_emoji_ok = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🟢 OK/active status"
    )
    tg_emoji_warn = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🟡 Warning status"
    )
    tg_emoji_critical = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🔴 Critical/down status"
    )
    tg_emoji_chart = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 📊 Reports/charts"
    )
    tg_emoji_alert = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🚨 Alert notifications"
    )
    tg_emoji_money = models.CharField(max_length=30, blank=True, default='', help_text="💰 Tariff/pricing")
    tg_emoji_clock = models.CharField(max_length=30, blank=True, default='', help_text="🕐 Timestamp")
    tg_emoji_uptime = models.CharField(max_length=30, blank=True, default='', help_text="⏱ Uptime")
    tg_emoji_load = models.CharField(max_length=30, blank=True, default='', help_text="📈 Load average")
    tg_emoji_swap = models.CharField(max_length=30, blank=True, default='', help_text="🔄 Swap")
    tg_emoji_services_icon = models.CharField(max_length=30, blank=True, default='', help_text="🔧 Services section")
    tg_emoji_trophy = models.CharField(max_length=30, blank=True, default='', help_text="🏆 Top processes")
    tg_emoji_nginx = models.CharField(max_length=30, blank=True, default='', help_text="⚡ nginx icon")
    tg_emoji_postgresql = models.CharField(max_length=30, blank=True, default='', help_text="🐘 PostgreSQL icon")
    tg_emoji_package = models.CharField(max_length=30, blank=True, default='', help_text="📦 Plan package")
    tg_emoji_upgrade = models.CharField(max_length=30, blank=True, default='', help_text="⬆️ Upgrade")
    tg_emoji_downgrade = models.CharField(max_length=30, blank=True, default='', help_text="⬇️ Downgrade")

    # ── Notification Emoji ──
    tg_emoji_reply = models.CharField(max_length=30, blank=True, default='', help_text="↩️ Reply")
    tg_emoji_like = models.CharField(max_length=30, blank=True, default='', help_text="👍 Like")
    tg_emoji_unlike = models.CharField(max_length=30, blank=True, default='', help_text="👎 Unlike")
    tg_emoji_contact_msg = models.CharField(max_length=30, blank=True, default='', help_text="📩 Contact")

    # ── Admin Log Emoji ──
    tg_emoji_user = models.CharField(max_length=30, blank=True, default='', help_text="👤 User")
    tg_emoji_returning = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🔄 Returning user"
    )
    tg_emoji_premium = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for ⭐️ Premium badge"
    )
    tg_emoji_osint = models.CharField(
        max_length=30, blank=True, default='',
        help_text="Custom emoji ID for 🔍 OSINT button"
    )
    tg_emoji_education = models.CharField(max_length=30, blank=True, default='', help_text="🎓 TalabaOvozi")
    tg_emoji_group = models.CharField(max_length=30, blank=True, default='', help_text="👥 Group/supergroup")
    tg_emoji_channel_icon = models.CharField(max_length=30, blank=True, default='', help_text="📢 Channel entity")
    tg_emoji_id_badge = models.CharField(max_length=30, blank=True, default='', help_text="🆔 Telegram ID")
    tg_emoji_phone = models.CharField(max_length=30, blank=True, default='', help_text="📱 Phone number")
    tg_emoji_sources = models.CharField(max_length=30, blank=True, default='', help_text="📡 Service sources")
    tg_emoji_crown = models.CharField(max_length=30, blank=True, default='', help_text="👑 Admin count")
    tg_emoji_verified = models.CharField(max_length=30, blank=True, default='', help_text="✅ Verified badge")
    tg_emoji_scam_warn = models.CharField(max_length=30, blank=True, default='', help_text="⚠️ SCAM/warning")
    tg_emoji_history = models.CharField(max_length=30, blank=True, default='', help_text="📝 Username history")
    tg_emoji_pencil = models.CharField(max_length=30, blank=True, default='', help_text="✏️ Name history")
    tg_emoji_calendar = models.CharField(max_length=30, blank=True, default='', help_text="📅 Activity dates")

    # ── Command Emoji ──
    tg_emoji_greeting = models.CharField(max_length=30, blank=True, default='', help_text="👋 Greeting")
    tg_emoji_ban = models.CharField(max_length=30, blank=True, default='', help_text="🚫 Ban")
    tg_emoji_mute = models.CharField(max_length=30, blank=True, default='', help_text="🔇 Mute")
    tg_emoji_lock = models.CharField(max_length=30, blank=True, default='', help_text="🔒 Lock")
    tg_emoji_notifications_icon = models.CharField(max_length=30, blank=True, default='', help_text="🔔 Notifications")
    tg_emoji_config_icon = models.CharField(max_length=30, blank=True, default='', help_text="⚙️ Config")
    tg_emoji_error = models.CharField(max_length=30, blank=True, default='', help_text="❌ Error")
    tg_emoji_success = models.CharField(max_length=30, blank=True, default='', help_text="✅ Success")
    tg_emoji_backup_icon = models.CharField(max_length=30, blank=True, default='', help_text="💾 Backup")
    tg_emoji_logs_icon = models.CharField(max_length=30, blank=True, default='', help_text="📋 Logs")

    # ── Channel Sharing Emoji ──
    tg_emoji_post = models.CharField(max_length=30, blank=True, default='', help_text="📝 Blog post")
    tg_emoji_project = models.CharField(max_length=30, blank=True, default='', help_text="📱 Project")
    tg_emoji_tech = models.CharField(max_length=30, blank=True, default='', help_text="🛠 Tech stack")

    # ── Bot Status ──
    tg_emoji_warning = models.CharField(max_length=30, blank=True, default='', help_text="⚠️ Warning")
    tg_emoji_red_dot = models.CharField(max_length=30, blank=True, default='', help_text="🔴 Red dot")
    tg_emoji_green_dot = models.CharField(max_length=30, blank=True, default='', help_text="🟢 Green dot")
    tg_emoji_blocked = models.CharField(max_length=30, blank=True, default='', help_text="🚫 Blocked")

    # ── Bot Actions ──
    tg_emoji_plus = models.CharField(max_length=30, blank=True, default='', help_text="➕ Add")
    tg_emoji_minus = models.CharField(max_length=30, blank=True, default='', help_text="➖ Remove")
    tg_emoji_edit = models.CharField(max_length=30, blank=True, default='', help_text="✏️ Edit")
    tg_emoji_right_arrow = models.CharField(max_length=30, blank=True, default='', help_text="➡️ Right arrow")

    # ── Bot Navigation ──
    tg_emoji_point_right = models.CharField(max_length=30, blank=True, default='', help_text="👉 Point right")
    tg_emoji_point_down = models.CharField(max_length=30, blank=True, default='', help_text="👇 Point down")
    tg_emoji_back = models.CharField(max_length=30, blank=True, default='', help_text="🔙 Back")
    tg_emoji_home = models.CharField(max_length=30, blank=True, default='', help_text="🏠 Home")

    # ── Bot Awards ──
    tg_emoji_gold = models.CharField(max_length=30, blank=True, default='', help_text="🥇 Gold/1st")
    tg_emoji_silver = models.CharField(max_length=30, blank=True, default='', help_text="🥈 Silver/2nd")
    tg_emoji_bronze = models.CharField(max_length=30, blank=True, default='', help_text="🥉 Bronze/3rd")

    # ── Bot People ──
    tg_emoji_person = models.CharField(max_length=30, blank=True, default='', help_text="👤 Person")
    tg_emoji_people = models.CharField(max_length=30, blank=True, default='', help_text="👥 People")
    tg_emoji_teacher = models.CharField(max_length=30, blank=True, default='', help_text="👨‍🏫 Teacher")
    tg_emoji_crown_icon = models.CharField(max_length=30, blank=True, default='', help_text="👑 Crown icon")
    tg_emoji_eye = models.CharField(max_length=30, blank=True, default='', help_text="👁 Eye")

    # ── Bot Communication ──
    tg_emoji_mail = models.CharField(max_length=30, blank=True, default='', help_text="📨 Mail")
    tg_emoji_upload = models.CharField(max_length=30, blank=True, default='', help_text="📤 Upload")
    tg_emoji_email_icon = models.CharField(max_length=30, blank=True, default='', help_text="📧 Email")
    tg_emoji_phone_icon = models.CharField(max_length=30, blank=True, default='', help_text="📞 Phone")
    tg_emoji_thought = models.CharField(max_length=30, blank=True, default='', help_text="💭 Thought bubble")
    tg_emoji_speech = models.CharField(max_length=30, blank=True, default='', help_text="💬 Speech bubble")

    # ── Bot Data ──
    tg_emoji_stats = models.CharField(max_length=30, blank=True, default='', help_text="📊 Stats")
    tg_emoji_growth = models.CharField(max_length=30, blank=True, default='', help_text="📈 Growth")
    tg_emoji_document = models.CharField(max_length=30, blank=True, default='', help_text="📄 Document")
    tg_emoji_name_badge = models.CharField(max_length=30, blank=True, default='', help_text="📛 Name badge")
    tg_emoji_mobile = models.CharField(max_length=30, blank=True, default='', help_text="📱 Mobile")
    tg_emoji_device = models.CharField(max_length=30, blank=True, default='', help_text="📲 Device")
    tg_emoji_numbers = models.CharField(max_length=30, blank=True, default='', help_text="🔢 Numbers")

    # ── Bot System ──
    tg_emoji_settings = models.CharField(max_length=30, blank=True, default='', help_text="⚙️ Settings")
    tg_emoji_secure = models.CharField(max_length=30, blank=True, default='', help_text="🔐 Secure")
    tg_emoji_locked = models.CharField(max_length=30, blank=True, default='', help_text="🔒 Locked")
    tg_emoji_key = models.CharField(max_length=30, blank=True, default='', help_text="🔑 Key")
    tg_emoji_shield = models.CharField(max_length=30, blank=True, default='', help_text="🛡 Shield")
    tg_emoji_cloud = models.CharField(max_length=30, blank=True, default='', help_text="☁️ Cloud")

    # ── Bot Misc ──
    tg_emoji_globe = models.CharField(max_length=30, blank=True, default='', help_text="🌐 Globe")
    tg_emoji_moon = models.CharField(max_length=30, blank=True, default='', help_text="🌙 Moon")
    tg_emoji_clover = models.CharField(max_length=30, blank=True, default='', help_text="🍀 Clover")
    tg_emoji_target = models.CharField(max_length=30, blank=True, default='', help_text="🎯 Target")
    tg_emoji_diamond = models.CharField(max_length=30, blank=True, default='', help_text="💎 Diamond")
    tg_emoji_control = models.CharField(max_length=30, blank=True, default='', help_text="🎛 Control")
    tg_emoji_fire = models.CharField(max_length=30, blank=True, default='', help_text="🔥 Fire")
    tg_emoji_triangle = models.CharField(max_length=30, blank=True, default='', help_text="🔺 Triangle")
    tg_emoji_graduation = models.CharField(max_length=30, blank=True, default='', help_text="🎓 Graduation")
    tg_emoji_pray = models.CharField(max_length=30, blank=True, default='', help_text="🙏 Pray")
    tg_emoji_school = models.CharField(max_length=30, blank=True, default='', help_text="🏫 School")
    tg_emoji_ballot = models.CharField(max_length=30, blank=True, default='', help_text="🗳 Ballot box")
    tg_emoji_blue_square = models.CharField(max_length=30, blank=True, default='', help_text="🟦 Blue square")
    tg_emoji_lightning = models.CharField(max_length=30, blank=True, default='', help_text="⚡ Lightning")
    tg_emoji_celebration = models.CharField(max_length=30, blank=True, default='', help_text="🎉 Celebration")
    tg_emoji_memo = models.CharField(max_length=30, blank=True, default='', help_text="📝 Memo/write")
    tg_emoji_pin = models.CharField(max_length=30, blank=True, default='', help_text="📍 Pin/location")
    tg_emoji_undo = models.CharField(max_length=30, blank=True, default='', help_text="↩️ Undo")
    tg_emoji_skip = models.CharField(max_length=30, blank=True, default='', help_text="⏭ Skip")

    # ── Dynamic extras ──
    tg_emoji_extra = models.JSONField(
        default=dict, blank=True,
        help_text='Extra custom emoji IDs as JSON.'
    )

    class Meta:
        abstract = True


class FooterMixin(models.Model):
    """Footer text, social overrides, and copyright."""

    footer_description = models.TextField(
        max_length=500, blank=True, default="",
        help_text="Footer description text (leave blank to use site_tagline)"
    )
    # footer_email removed — always uses main email field
    footer_social_github = models.URLField(
        blank=True, default="",
        help_text="Footer GitHub URL (leave blank to inherit from main socials)"
    )
    footer_social_linkedin = models.URLField(
        blank=True, default="",
        help_text="Footer LinkedIn URL (leave blank to inherit from main socials)"
    )
    footer_social_twitter = models.URLField(
        blank=True, default="",
        help_text="Footer Twitter/X URL (leave blank to inherit from main socials)"
    )
    footer_social_telegram = models.URLField(
        blank=True, default="",
        help_text="Footer Telegram URL (leave blank to inherit from main socials)"
    )
    footer_text = models.CharField(
        max_length=255, default="© 2026 Jahongir Kuziboev. All rights reserved.",
        help_text="Footer copyright line"
    )

    class Meta:
        abstract = True


# ── Editorial v3 dynamic content (manifesto, process, ticker, values, badges) ──
class EditorialContentMixin(models.Model):
    """All copy/content for the v3 editorial site that should be admin-editable."""

    # Hero meta-line items
    hero_volume_label = models.CharField(max_length=80, blank=True, default="Vol. 03 · Issue 01")
    hero_location = models.CharField(max_length=80, blank=True, default="Tashkent · 41.2995° N")
    hero_scroll_label = models.CharField(max_length=80, blank=True, default="Scroll · Begin transmission")
    hero_section_count = models.CharField(max_length=24, blank=True, default="01 / 07")
    hero_eyebrow = models.CharField(
        max_length=160, blank=True,
        default="Personal · Build Studio · VibeCoder",
    )

    # Brand line under wordmark
    brand_tagline = models.CharField(max_length=80, blank=True, default="Build Studio · Est. 2022")
    footer_volume = models.CharField(max_length=80, blank=True, default="VOL. 03 · ISSUE 01")

    # Ticker (JSON array of strings)
    ticker_items = models.JSONField(
        blank=True, default=list,  # populated by SiteSettings.load() if empty
        help_text="Marquee ticker items, e.g. ['Flutter mobile engineering', 'Production apps', ...]",
    )

    # Manifesto section
    manifesto_eyebrow = models.CharField(max_length=80, blank=True, default="02 — Philosophy")
    manifesto_title = models.CharField(max_length=160, blank=True, default="Manifesto.")
    manifesto_label = models.CharField(max_length=80, blank=True, default="03 PRINCIPLES · ON BUILDING")
    manifesto_principles = models.JSONField(
        blank=True, default=list,
        help_text="List of {n, title, description} dicts. n is shown as a giant numeral (e.g. '01').",
    )

    # Metrics section
    metrics_eyebrow = models.CharField(max_length=80, blank=True, default="03 — By the numbers")
    metrics_title = models.CharField(
        max_length=240, blank=True,
        default='A track record,<br><em style="font-weight: 300;">measured.</em>',
        help_text="HTML allowed. Use <br> for line breaks and <em> for italic emphasis.",
    )
    metrics_description = models.TextField(
        blank=True,
        default="Numbers from live production apps over the last four years. Pulled from dashboards, not pitch decks.",
    )

    # Process / How I work
    process_eyebrow = models.CharField(max_length=80, blank=True, default="05 — How I work")
    process_title = models.CharField(
        max_length=240, blank=True,
        default='Five steps,<br><em style="font-weight: 300;">no surprises.</em>',
        help_text="HTML allowed. Use <br> for line breaks and <em> for italic emphasis.",
    )
    process_steps = models.JSONField(
        blank=True, default=list,
        help_text="List of {n, title, description} dicts.",
    )

    # CTA section
    cta_eyebrow = models.CharField(max_length=80, blank=True, default="07 — Open channel")
    cta_title_pre = models.CharField(
        max_length=240, blank=True,
        default="Bring the<br>brief.",
        help_text="HTML allowed. Use <br> for line breaks.",
    )
    cta_title_em = models.CharField(max_length=120, blank=True, default="I'll bring the team.")
    cta_description = models.TextField(
        blank=True,
        default="Two slots opening for Q2 2026. Best fit: ambitious web apps, Telegram bot products, or AI-augmented systems with a 12+ week runway and a real user base in mind.",
    )
    cta_button_text = models.CharField(max_length=80, blank=True, default="Start a conversation")
    cta_response_label = models.CharField(max_length=80, blank=True, default="Avg. response · 4–6h")

    # Contact page
    contact_form_label = models.CharField(max_length=80, blank=True, default="Brief / Form 7741")
    contact_form_title = models.CharField(max_length=160, blank=True, default="Tell me what you're building.")
    contact_availability_status = models.CharField(max_length=80, blank=True, default="Available · Q2 2026")
    contact_availability_note = models.CharField(
        max_length=240, blank=True,
        default="Two engagement slots open. Tashkent, UTC+5.",
    )

    # Studio (Team) page
    team_hero_eyebrow = models.CharField(max_length=80, blank=True, default="Studio · Crew Manifest")
    team_section_label = models.CharField(max_length=80, blank=True, default="Section · 03")
    team_studio_label = models.CharField(max_length=80, blank=True, default="Studio open · Tashkent")
    team_intro = models.TextField(
        blank=True,
        default="A small studio of full-stack builders, designers, and operators. We ship production web apps, Telegram bots, and AI-augmented systems — using whatever tool fits the problem.",
    )
    team_values_eyebrow = models.CharField(max_length=80, blank=True, default="Operating principles")
    team_values_title = models.CharField(
        max_length=240, blank=True,
        default='How we<br>think.',
        help_text="HTML allowed. Use <br> for line breaks.",
    )
    team_values_intro = models.CharField(
        max_length=300, blank=True,
        default="Six values, four years together. These aren't slogans on a wall — they're the trade-offs we keep landing on.",
    )
    team_values = models.JSONField(
        blank=True, default=list,
        help_text="List of {title, description} dicts.",
    )

    # Availability badge (used on hero + footer)
    availability_badge = models.CharField(max_length=120, blank=True, default="Now booking · Q2 2026")

    # ── Section labels (replace hardcoded "Section · 02" etc.) ────────────────
    about_section_eyebrow = models.CharField(max_length=80, blank=True, default="About · Operator")
    projects_section_label = models.CharField(max_length=80, blank=True, default="Section · 02")
    blog_section_label = models.CharField(max_length=80, blank=True, default="Section · 04")
    contact_section_label = models.CharField(max_length=80, blank=True, default="Section · 05")
    blog_section_status = models.CharField(max_length=80, blank=True, default="New every fortnight")
    contact_section_channels = models.CharField(max_length=80, blank=True, default="4 channels open")

    # ── Team page headline (was hardcoded) ────────────────────────────────────
    team_hero_headline = models.CharField(
        max_length=300, blank=True,
        default='Behind every<br>strong product is a<br><em>focused</em> team.',
        help_text="HTML allowed (<br>, <em>). Big serif headline on /team/.",
    )

    # ── Footer CTA (was hardcoded in base.html) ───────────────────────────────
    footer_cta_eyebrow = models.CharField(
        max_length=120, blank=True,
        default="End / Transmission complete",
    )
    footer_cta_headline = models.CharField(
        max_length=400, blank=True,
        default='Got a brief?<br><em>Let\'s </em>open a channel.',
        help_text="HTML allowed. Footer ink-block CTA headline.",
    )
    footer_practice_items = models.JSONField(
        blank=True, default=list,
        help_text="List of practice/service strings, e.g. ['Web apps · Django', 'Telegram bots · Aiogram', ...]",
    )

    # ── Error page copy (was hardcoded in 404/500/section_unavailable) ────────
    error_404_headline = models.CharField(
        max_length=300, blank=True,
        default='Looks like this page<br><em style="font-weight: 400;">drifted off the map.</em>',
        help_text="HTML allowed.",
    )
    error_404_description = models.TextField(
        blank=True,
        default="The page you're looking for has either been moved, archived, or never existed in the first place. Let's get you back on track.",
    )
    error_500_headline = models.CharField(
        max_length=300, blank=True,
        default='Something on our<br><em style="font-weight: 400;">end snapped.</em>',
        help_text="HTML allowed.",
    )
    error_500_description = models.TextField(
        blank=True,
        default="An internal error occurred and the page couldn't render. The team has been notified — try again in a moment, or head back home.",
    )
    error_unavailable_headline = models.CharField(
        max_length=300, blank=True,
        default='This section is<br><em style="font-weight: 400;">temporarily offline.</em>',
        help_text="HTML allowed. Shown on /projects/ when apps_section_visible=False.",
    )
    error_unavailable_description = models.TextField(
        blank=True,
        default="This part of the site is temporarily offline. Check back soon — it should be up again shortly.",
    )

    class Meta:
        abstract = True


def _default_ticker():
    return [
        "VibeCoder",
        "AI-augmented development",
        "Web apps · Telegram bots · Full-stack",
        "Tashkent — worldwide remote",
        "Built for scale, not for demos",
    ]


def _default_manifesto():
    return [
        {"n": "01", "title": "Code is a side effect of thinking clearly.",
         "description": "A clean codebase is the residue of a clear understanding of the problem. I don't ship spaghetti and call it pragmatic."},
        {"n": "02", "title": "Production is the only opinion that matters.",
         "description": "Demos are theatre. I measure my work by App Store reviews, crash-free sessions, and revenue clients can count."},
        {"n": "03", "title": "Boring infrastructure is high craft.",
         "description": "CI that never fails. Migrations that never lose data. Observability you actually use. The unglamorous parts are where senior engineers earn their fee."},
    ]


def _default_process():
    return [
        {"n": "01", "title": "Diagnose",
         "description": "A 60-minute call. We map the actual problem behind the brief — not the symptom."},
        {"n": "02", "title": "Architect",
         "description": "A 1-week sprint to lay out the data model, state shape, integration surfaces. No code yet."},
        {"n": "03", "title": "Build in slices",
         "description": "End-to-end working features each week. Staging deploy from day 7, AI-augmented iteration."},
        {"n": "04", "title": "Harden + ship",
         "description": "Beta with real users, telemetry wired, rollback plan agreed. Then production deploy with one command."},
        {"n": "05", "title": "Operate",
         "description": "Optional retainer. Incident triage, telemetry reviews — the boring middle that keeps things alive."},
    ]


def _default_team_values():
    return [
        {"title": "Clean code", "description": "Code that the next engineer can read without a meeting."},
        {"title": "Scalable architecture", "description": "Built for v3 — not just v1."},
        {"title": "Product thinking", "description": "We ask 'why' before 'how'."},
        {"title": "Fast delivery", "description": "Two-week sprints, Friday demos, no surprises."},
        {"title": "Long-term support", "description": "We don't hand off and disappear."},
        {"title": "Production-first", "description": "Real users, real reviews, real revenue."},
    ]


def _default_practice():
    return [
        "Web apps · Django",
        "Telegram bots · Aiogram",
        "AI-augmented systems",
        "Design systems",
    ]


# ── Concrete Model ───────────────────────────────────────────────────────────────


class SiteSettings(
    BrandingMixin,
    SEOMixin,
    NavigationMixin,
    HeroMixin,
    ContentSectionsMixin,
    ContactSocialsMixin,
    TelegramMixin,
    FooterMixin,
    EditorialContentMixin,
    models.Model,
):
    """
    Singleton model — all dynamic site configuration lives here.
    One instance, managed via Django admin. Access via SiteSettings.load().
    Cache invalidation handled by SiteSettingsService.

    Fields are organized into abstract mixins for readability:
    BrandingMixin, SEOMixin, NavigationMixin, HeroMixin,
    ContentSectionsMixin, ContactSocialsMixin, TelegramMixin, FooterMixin.
    """

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

    # ── Computed properties (footer fallbacks) ────────────────────────────────

    @property
    def display_logo_text(self):
        """Logo text with fallback to site_author."""
        return self.logo_text or self.site_author

    @property
    def visitor_count(self):
        """Total unique visitors tracked by PageView (cached 1 hour)."""
        key = 'visitor_count'
        count = cache.get(key)
        if count is None:
            count = PageView.objects.count()
            cache.set(key, count, 60 * 60)
        return count

    @property
    def footer_display_description(self):
        """Footer description with fallback to site_tagline."""
        return self.footer_description or self.site_tagline

    @property
    def footer_display_email(self):
        """Always uses main email."""
        return self.email

    # ── Editorial v3 content resolvers (return field if set, else seed defaults) ──

    @property
    def ticker_items_resolved(self):
        return self.ticker_items if self.ticker_items else _default_ticker()

    @property
    def manifesto_principles_resolved(self):
        return self.manifesto_principles if self.manifesto_principles else _default_manifesto()

    @property
    def process_steps_resolved(self):
        return self.process_steps if self.process_steps else _default_process()

    @property
    def team_values_resolved(self):
        return self.team_values if self.team_values else _default_team_values()

    @property
    def footer_practice_items_resolved(self):
        return self.footer_practice_items if self.footer_practice_items else _default_practice()

    @property
    def footer_display_github(self):
        return self.footer_social_github or self.github_url

    @property
    def footer_display_linkedin(self):
        return self.footer_social_linkedin or self.linkedin_url

    @property
    def footer_display_twitter(self):
        return self.footer_social_twitter or self.twitter_url

    @property
    def footer_display_telegram(self):
        return self.footer_social_telegram or self.telegram_url


class PageView(models.Model):
    """
    Tracks unique site visitors via cookie + IP deduplication.
    - Same browser, refresh → cookie prevents duplicate
    - Different browser, same device/network → IP prevents duplicate
    - Incognito mode → IP prevents duplicate
    - New device/network → new record
    """
    visitor_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Site Visitor"
        verbose_name_plural = "Site Visitors"
        ordering = ['-created_at']

    def __str__(self):
        return f"Visitor {self.visitor_id} ({self.ip_address}) — {self.created_at:%Y-%m-%d %H:%M}"


# ── Asset Manager ────────────────────────────────────────────────────────────
class Asset(models.Model):
    """Editorial Asset Manager — uploaded media with auto-extracted metadata."""

    FOLDER_CHOICES = [
        ('hero', 'Hero'),
        ('apps', 'Apps'),
        ('team', 'Team'),
        ('journal', 'Journal'),
        ('brand', 'Brand'),
        ('product', 'Product'),
        ('experience', 'Experience'),
        ('misc', 'Misc'),
    ]

    SOURCE_CHOICES = [
        ('upload', 'Manual upload'),
        ('imported', 'Imported from media'),
        ('linked', 'Linked from model'),
    ]

    file = models.FileField(upload_to='assets/%Y/%m/')
    name = models.CharField(max_length=200, blank=True, help_text="Auto-derived from filename if blank")
    folder = models.CharField(max_length=24, choices=FOLDER_CHOICES, default='misc', db_index=True)
    alt_text = models.CharField(max_length=240, blank=True, help_text="Optional accessibility description")

    # Source tracking — used by the import command to dedupe
    source = models.CharField(max_length=12, choices=SOURCE_CHOICES, default='upload')
    source_path = models.CharField(
        max_length=500, blank=True, db_index=True,
        help_text="Original media-relative path (used to dedupe imports)",
    )

    # Auto-extracted metadata (populated on save)
    format = models.CharField(max_length=10, blank=True, help_text="JPG, PNG, SVG, WEBP, MP4, etc.")
    size_bytes = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0, help_text="0 if not an image")
    height = models.PositiveIntegerField(default=0)

    # Usage tracking (denormalized count refreshed by signal/import)
    usage_count = models.PositiveIntegerField(default=0, help_text="How many model fields reference this file")
    usage_summary = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated list of where this asset is used, e.g. 'Project: Halyk Pay, SiteSettings: hero_image'",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'

    def __str__(self):
        return self.name or self.file.name.split('/')[-1]

    def save(self, *args, **kwargs):
        # Skip auto-extraction if metadata is already set (e.g. import command pre-populates it)
        skip_extraction = kwargs.pop('skip_extraction', False) or (self.format and self.size_bytes)
        if self.file and not skip_extraction:
            if not self.name:
                self.name = self.file.name.split('/')[-1].rsplit('.', 1)[0][:200]
            ext = self.file.name.rsplit('.', 1)[-1].upper() if '.' in self.file.name else ''
            self.format = ext[:10]
            try:
                self.size_bytes = self.file.size
            except (FileNotFoundError, OSError, ValueError):
                pass
            if ext in {'JPG', 'JPEG', 'PNG', 'GIF', 'WEBP', 'BMP'}:
                try:
                    from PIL import Image
                    self.file.seek(0)
                    with Image.open(self.file) as img:
                        self.width, self.height = img.size
                    self.file.seek(0)
                except Exception:
                    pass
        super().save(*args, **kwargs)

    @property
    def size_human(self):
        n = self.size_bytes
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / 1024 / 1024:.2f} MB"

    @property
    def dimensions(self):
        if self.width and self.height:
            return f"{self.width}×{self.height}"
        return "—"

    @property
    def is_image(self):
        return self.format.upper() in {'JPG', 'JPEG', 'PNG', 'GIF', 'WEBP', 'SVG', 'BMP'}

    @property
    def asset_id(self):
        return f"AST-{self.pk:04d}"
