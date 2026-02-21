# Safe non-destructive migration: only AddField and CreateModel.
# No AlterField, RemoveField, or data mutations. Existing rows remain intact.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0001_initial'),
    ]

    operations = [
        # ── Skill: add category + order ───────────────────────────────────────
        migrations.AddField(
            model_name='skill',
            name='category',
            field=models.CharField(
                choices=[
                    ('mobile', 'Mobile'),
                    ('architecture', 'Architecture'),
                    ('backend', 'Backend & Networking'),
                    ('database', 'Databases'),
                    ('devops', 'DevOps & Tools'),
                    ('uiux', 'UI/UX'),
                    ('other', 'Other'),
                ],
                default='other',
                help_text='Skill category for grouped display',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='skill',
            name='order',
            field=models.IntegerField(default=0, help_text='Display order within category'),
        ),

        # ── Skill: update ordering ────────────────────────────────────────────
        migrations.AlterModelOptions(
            name='skill',
            options={'ordering': ['category', 'order', 'name']},
        ),

        # ── Project: add mobile-specific fields ──────────────────────────────
        migrations.AddField(
            model_name='project',
            name='short_description',
            field=models.CharField(
                blank=True, max_length=300,
                help_text='One-liner for project cards (falls back to truncated description)',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='platform',
            field=models.CharField(
                choices=[
                    ('android', 'Android'),
                    ('ios', 'iOS'),
                    ('cross', 'Cross-platform (Android & iOS)'),
                    ('web', 'Web'),
                ],
                default='cross',
                help_text='Target platform',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='app_store_url',
            field=models.URLField(blank=True, help_text='Apple App Store link'),
        ),
        migrations.AddField(
            model_name='project',
            name='play_store_url',
            field=models.URLField(blank=True, help_text='Google Play Store link'),
        ),
        migrations.AddField(
            model_name='project',
            name='tech_stack',
            field=models.CharField(
                blank=True, max_length=500,
                help_text='Comma-separated tech stack (e.g. Flutter, BLoC, Dio, Firebase)',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='is_featured',
            field=models.BooleanField(
                default=False, help_text='Show on homepage featured section',
            ),
        ),

        # ── Project: make image optional (nullable) ──────────────────────────
        migrations.AlterField(
            model_name='project',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='projects/'),
        ),

        # ── Project: make technologies optional ──────────────────────────────
        migrations.AlterField(
            model_name='project',
            name='technologies',
            field=models.ManyToManyField(
                blank=True, related_name='projects', to='portfolio.skill',
            ),
        ),

        # ── Experience: add company_logo, company_url, location ──────────────
        migrations.AddField(
            model_name='experience',
            name='company_logo',
            field=models.ImageField(
                blank=True, null=True, upload_to='experience/',
                help_text='Company logo (optional, 128x128 recommended)',
            ),
        ),
        migrations.AddField(
            model_name='experience',
            name='company_url',
            field=models.URLField(blank=True, help_text='Company website URL'),
        ),
        migrations.AddField(
            model_name='experience',
            name='location',
            field=models.CharField(
                blank=True, max_length=100,
                help_text='e.g. Tashkent, Uzbekistan',
            ),
        ),

        # ── ProjectScreenshot: new model ─────────────────────────────────────
        migrations.CreateModel(
            name='ProjectScreenshot',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID',
                )),
                ('image', models.ImageField(upload_to='projects/screenshots/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('order', models.IntegerField(default=0)),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='screenshots',
                    to='portfolio.project',
                )),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]
