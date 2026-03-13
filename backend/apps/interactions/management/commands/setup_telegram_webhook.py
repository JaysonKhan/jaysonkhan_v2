"""
Register (or delete) the Telegram bot webhook.

Usage:
    python manage.py setup_telegram_webhook           # register
    python manage.py setup_telegram_webhook --delete   # remove
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from interactions.notifications.telegram_api import TelegramBotAPI


class Command(BaseCommand):
    help = 'Register or delete the Telegram bot webhook URL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete the webhook instead of setting it',
        )

    def handle(self, *args, **options):
        api = TelegramBotAPI()

        if options['delete']:
            result = api.delete_webhook()
            self.stdout.write(self.style.SUCCESS(f'Webhook deleted: {result}'))
            return

        secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        domain = getattr(settings, 'TELEGRAM_WEBHOOK_DOMAIN', '')

        if not secret:
            self.stderr.write(self.style.ERROR(
                'TELEGRAM_WEBHOOK_SECRET is not set. '
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            ))
            return

        if not domain:
            self.stderr.write(self.style.ERROR(
                'TELEGRAM_WEBHOOK_DOMAIN is not set (e.g. https://jaysonkhan.com)'
            ))
            return

        url = f'{domain}/api/telegram/webhook/{secret}/'
        result = api.set_webhook(url, secret_token=secret)
        self.stdout.write(self.style.SUCCESS(f'Webhook set: {url}\nResult: {result}'))
