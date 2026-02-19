from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # ── Branding ──────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='site_author',
            field=models.CharField(
                default='JaysonKhan',
                help_text='Author name (used in blog byline and structured data)',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='site_author_initials',
            field=models.CharField(
                default='JK',
                help_text='2–3 letter initials for avatar badge',
                max_length=5,
            ),
        ),

        # ── SEO ───────────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='twitter_handle',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Twitter/X handle without @ — for twitter:site tag',
                max_length=50,
            ),
        ),

        # ── Navigation ────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='nav_cta_text',
            field=models.CharField(
                default='Hire Me',
                help_text='Navigation CTA button label',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='nav_cta_url',
            field=models.CharField(
                default='/contact/',
                help_text='Navigation CTA button URL (relative or absolute)',
                max_length=200,
            ),
        ),

        # ── Hero CTAs ─────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='hero_primary_cta_text',
            field=models.CharField(
                default='View Projects',
                help_text='Primary CTA button text in hero',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='hero_primary_cta_url',
            field=models.CharField(
                default='/projects/',
                help_text='Primary CTA button URL',
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='hero_secondary_cta_text',
            field=models.CharField(
                default='Contact Me',
                help_text='Secondary CTA button text in hero',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='hero_secondary_cta_url',
            field=models.CharField(
                default='/contact/',
                help_text='Secondary CTA button URL',
                max_length=200,
            ),
        ),

        # ── Skills Section ────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='skills_section_title',
            field=models.CharField(
                default='My Expertise',
                help_text='Skills section heading',
                max_length=100,
            ),
        ),

        # ── Featured Projects Section ──────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='featured_projects_title',
            field=models.CharField(
                default='Featured Projects',
                help_text='Featured projects section heading',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='featured_projects_subtitle',
            field=models.CharField(
                default='Some of my best architectural work.',
                help_text='Featured projects section sub-heading',
                max_length=255,
            ),
        ),

        # ── Latest Blog Section ───────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='latest_blog_title',
            field=models.CharField(
                default='Latest from the Blog',
                help_text='Latest blog section heading on homepage',
                max_length=100,
            ),
        ),

        # ── Projects Page ─────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='projects_page_title',
            field=models.CharField(
                default='Portfolio Projects',
                help_text='Projects page <h1> heading',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='projects_page_subtitle',
            field=models.CharField(
                default='A detailed look at the systems and applications I\u2019ve architected and implemented.',
                help_text='Projects page sub-heading',
                max_length=255,
            ),
        ),

        # ── Blog Page ─────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='blog_page_title',
            field=models.CharField(
                default='The Blog',
                help_text='Blog list page <h1> heading',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='blog_page_subtitle',
            field=models.CharField(
                default='Insights on software architecture, backend engineering, and the future of web development.',
                help_text='Blog list page sub-heading',
                max_length=255,
            ),
        ),

        # ── Contact Page ──────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='contact_page_title',
            field=models.CharField(
                default='Get in touch',
                help_text='Contact page <h1> heading',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_page_subtitle',
            field=models.CharField(
                default='Have a project in mind or just want to chat architectural patterns? Drop me a message.',
                help_text='Contact page intro paragraph',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_email_label',
            field=models.CharField(
                default='Email',
                help_text='Label for email contact block',
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='contact_linkedin_label',
            field=models.CharField(
                default='LinkedIn',
                help_text='Label for LinkedIn contact block',
                max_length=50,
            ),
        ),

        # ── Socials ───────────────────────────────────────────────────────────
        migrations.AddField(
            model_name='sitesettings',
            name='twitter_url',
            field=models.URLField(
                blank=True,
                default='',
                help_text='Twitter/X profile URL (optional)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='telegram_url',
            field=models.URLField(
                blank=True,
                default='',
                help_text='Telegram profile URL (optional)',
            ),
        ),
    ]
