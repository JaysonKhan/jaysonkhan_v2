# Generated migration for SiteSettings model

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_title', models.CharField(default='JaysonKhan | Portfolio', help_text='Site title for <title> tag and branding', max_length=255)),
                ('site_tagline', models.CharField(default='Senior Python Backend Architect & Full-stack Developer.', help_text='Brief site description', max_length=500)),
                ('favicon', models.ImageField(blank=True, help_text='Favicon (appears in browser tab)', null=True, upload_to='branding/')),
                ('logo', models.ImageField(blank=True, help_text='Site logo (optional, for future use)', null=True, upload_to='branding/')),
                ('meta_description', models.TextField(default='Senior Python Backend Architect specializing in Django, PostgreSQL, and Clean Architecture. Available for freelance and full-time work.', help_text='Google search result description (max 160 characters)', max_length=160)),
                ('meta_keywords', models.CharField(default='Python, Django, PostgreSQL, Backend Developer, Software Architect, Portfolio', help_text='Comma-separated keywords for SEO', max_length=255)),
                ('og_image', models.ImageField(blank=True, help_text='Open Graph image (Facebook, LinkedIn, Telegram preview)', null=True, upload_to='seo/')),
                ('og_url', models.URLField(default='https://jaysonkhan.com', help_text='Open Graph URL')),
                ('hero_title', models.CharField(default='I build high-performance backend systems.', help_text='Main hero section heading', max_length=255)),
                ('hero_subtitle', models.TextField(default='Senior Python Backend Architect specializing in Django, PostgreSQL, and Clean Architecture.', help_text='Hero section subheading', max_length=500)),
                ('hero_image', models.ImageField(blank=True, help_text='Hero section image', null=True, upload_to='hero/')),
                ('hero_availability_badge', models.CharField(default='Available for work', help_text='Badge text above hero title', max_length=100)),
                ('about_title', models.CharField(default='About Me', help_text='About section heading', max_length=255)),
                ('about_description', models.TextField(default='Men 5+ yillik tajribaga ega Python backend arxitektiman. Django, FastAPI, PostgreSQL, Redis va Docker bilan professional darajada ishlayman. Clean Architecture va SOLID tamoyillariga amal qilgan holda yuqori samarali backend tizimlarni loyihalayman.', help_text='About section content')),
                ('about_image', models.ImageField(blank=True, help_text='About section image', null=True, upload_to='about/')),
                ('resume_file', models.FileField(blank=True, help_text='CV/Resume PDF for download', null=True, upload_to='cv/')),
                ('resume_button_text', models.CharField(default='Download CV', help_text='Text for resume download button', max_length=50)),
                ('email', models.EmailField(default='jayson@jaysonkhan.com', help_text='Primary contact email', max_length=254)),
                ('footer_text', models.CharField(default='© 2026 JaysonKhan. All rights reserved.', help_text='Footer copyright text', max_length=255)),
                ('github_url', models.URLField(blank=True, default='https://github.com/jaysonkhan', help_text='GitHub profile URL')),
                ('linkedin_url', models.URLField(blank=True, default='https://linkedin.com/in/jaysonkhan', help_text='LinkedIn profile URL')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
