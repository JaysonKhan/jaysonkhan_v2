from django.db import migrations

# Humanize the footer CTA headline: drop the confusing "kanal ochish" (open a
# channel) metaphor in favour of a plain "let's talk" invite. uz/ru/en only —
# the Khorezm dialect (xo) column is deliberately left untouched.
NEW = {
    'footer_cta_headline': {
        'uz': "Loyihangiz bormi?<br><em>Keling, </em>suhbatlashamiz.",
        'ru': "Есть проект?<br><em>Давайте </em>обсудим.",
        'en': "Got a project?<br><em>Let's </em>talk.",
    },
}


def apply(apps, schema_editor):
    SiteSettings = apps.get_model('core', 'SiteSettings')
    for row in SiteSettings.objects.all():
        for field, by_lang in NEW.items():
            for lang, value in by_lang.items():
                attr = f"{field}_{lang}"
                if hasattr(row, attr):
                    setattr(row, attr, value)
        row.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0037_add_sitesettings_proxy_sections'),
    ]
    operations = [
        migrations.RunPython(apply, noop),
    ]
