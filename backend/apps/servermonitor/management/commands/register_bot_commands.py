"""
Register server monitor bot commands with Telegram so they appear
in the command menu for the bot owner.

Registers THREE command sets: the default (Uzbek — shown to any client
Telegram can't match), an explicit `uz` set, and a `ru` set. Descriptions
come from the same core.bot_i18n `cmd.*` keys the /start menu uses, so the
menu and BotFather list can never drift apart.
"""
from core.bot_i18n import t
from django.core.management.base import BaseCommand
from interactions.notifications.telegram_api import TelegramBotAPI

# Menu order (BotFather shows them in this order).
COMMAND_ORDER = (
    'panel', 'ip', 'status', 'services', 'web', 'ssl', 'errors',
    'disk', 'top', 'db', 'restart', 'tariff', 'logs', 'backup',
    'lang', 'start', 'notifications',
)


def _commands_for(lang: str) -> list[dict]:
    return [
        {'command': cmd, 'description': t(f'cmd.{cmd}', lang)[:256]}
        for cmd in COMMAND_ORDER
    ]


class Command(BaseCommand):
    help = 'Register bot commands with Telegram (default/uz + ru)'

    def handle(self, *args, **options):
        api = TelegramBotAPI()
        registered = 0
        # '' = default set (no language_code) → Uzbek for everyone unmatched.
        for code in ('', 'uz', 'ru'):
            lang = code or 'uz'
            payload: dict = {'commands': _commands_for(lang)}
            if code:
                payload['language_code'] = code
            result = api._post('setMyCommands', payload)
            if result and result.get('ok'):
                registered += 1
            else:
                self.stderr.write(self.style.ERROR(f'Failed ({code or "default"}): {result}'))
        if registered:
            self.stdout.write(self.style.SUCCESS(
                f'Registered {len(COMMAND_ORDER)} commands × {registered} language sets'
            ))
