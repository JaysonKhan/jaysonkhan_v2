"""
Register server monitor bot commands with Telegram so they appear
in the command menu for the bot owner.
"""
from django.core.management.base import BaseCommand
from interactions.notifications.telegram_api import TelegramBotAPI

BOT_COMMANDS = [
    {'command': 'panel', 'description': 'Boshqaruv paneli (hammasi bir joyda)'},
    {'command': 'ip', 'description': 'Admin IP allowlist (barcha saytlar)'},
    {'command': 'status', 'description': 'Server holati (quick snapshot)'},
    {'command': 'services', 'description': 'Systemd servislar holati'},
    {'command': 'web', 'description': 'Saytlar HTTP health + latency'},
    {'command': 'ssl', 'description': 'SSL sertifikat muddatlari'},
    {'command': 'errors', 'description': 'Xatoliklar soni (/errors [soat])'},
    {'command': 'disk', 'description': 'Disk ishlatilishi (batafsil)'},
    {'command': 'top', 'description': 'Top jarayonlar (CPU/RAM)'},
    {'command': 'db', 'description': 'PostgreSQL baza hajmlari'},
    {'command': 'restart', 'description': 'Servis restart (tasdiq bilan)'},
    {'command': 'tariff', 'description': 'Contabo tarif tavsiyasi'},
    {'command': 'logs', 'description': 'Servis loglari (/logs [servis] [qator])'},
    {'command': 'backup', 'description': 'PostgreSQL backup yaratish'},
    {'command': 'start', 'description': 'Botni ishga tushirish'},
    {'command': 'notifications', 'description': 'Bildirishnoma sozlamalari'},
]


class Command(BaseCommand):
    help = 'Register bot commands with Telegram'

    def handle(self, *args, **options):
        api = TelegramBotAPI()
        result = api._post('setMyCommands', {'commands': BOT_COMMANDS})
        if result and result.get('ok'):
            self.stdout.write(self.style.SUCCESS(
                f'Registered {len(BOT_COMMANDS)} commands with Telegram'
            ))
        else:
            self.stderr.write(self.style.ERROR(f'Failed: {result}'))
