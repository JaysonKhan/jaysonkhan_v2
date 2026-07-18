"""
Sync the bot's Telegram-side profile: command menus + name/description.

Command scopes (why the admin menu is visible now):
  - DEFAULT scope (default/uz/ru sets) carries ONLY the public commands
    (/start /notifications /lang) — regular users never see owner-only
    commands they can't use.
  - The owner's private chat gets a CHAT-SCOPED set with the FULL admin
    command list. Chat scope outranks every other scope in Telegram's
    precedence and refreshes promptly, bypassing the aggressive client-side
    cache that made the default-scope list "invisible" for the admin.

Profile texts (setMyName / setMyDescription / setMyShortDescription) come
from core.bot_i18n `bot.*` keys (default=uz + ru) and are compare-first:
Telegram rate-limits profile changes hard (429), so we GET the current
value and only SET when it actually differs — safe to run on every deploy.
"""
from core.bot_i18n import t
from django.core.management.base import BaseCommand
from interactions.notifications.telegram_api import TelegramBotAPI

# Public commands — everyone's menu (default scope).
PUBLIC_COMMANDS = ('start', 'notifications', 'lang')

# Full admin menu — owner's chat scope, in this order.
COMMAND_ORDER = (
    'panel', 'ip', 'status', 'services', 'web', 'ssl', 'errors',
    'disk', 'top', 'db', 'restart', 'tariff', 'logs', 'backup',
    'lang', 'start', 'notifications',
)

# (getter, setter, result_field, i18n_key)
_PROFILE_FIELDS = (
    ('getMyName', 'setMyName', 'name', 'bot.name'),
    ('getMyDescription', 'setMyDescription', 'description', 'bot.description'),
    ('getMyShortDescription', 'setMyShortDescription', 'short_description', 'bot.short'),
)


def _commands_for(lang: str, order: tuple = COMMAND_ORDER) -> list[dict]:
    return [
        {'command': cmd, 'description': t(f'cmd.{cmd}', lang)[:256]}
        for cmd in order
    ]


def register_owner_commands(api: TelegramBotAPI, chat_id: int, lang: str) -> bool:
    """(Re-)pin the full admin command list to the owner's private chat.

    Also called from the /lang callback so the owner's menu re-renders in
    the newly chosen language without waiting for the next deploy.
    """
    result = api._post('setMyCommands', {
        'commands': _commands_for(lang),
        'scope': {'type': 'chat', 'chat_id': chat_id},
    })
    return bool(result and result.get('ok'))


class Command(BaseCommand):
    help = 'Sync bot commands (public + owner chat scope) and profile texts with Telegram'

    def handle(self, *args, **options):
        api = TelegramBotAPI()

        # 1. Public menus: default set (uz) + explicit uz/ru variants.
        registered = 0
        for code in ('', 'uz', 'ru'):
            payload: dict = {'commands': _commands_for(code or 'uz', PUBLIC_COMMANDS)}
            if code:
                payload['language_code'] = code
            result = api._post('setMyCommands', payload)
            if result and result.get('ok'):
                registered += 1
            else:
                self.stderr.write(self.style.ERROR(f'Public set failed ({code or "default"}): {result}'))
        self.stdout.write(self.style.SUCCESS(
            f'Public commands: {len(PUBLIC_COMMANDS)} × {registered} language sets'
        ))

        # 2. Full admin menu pinned to the owner's chat, in the owner's language.
        from core.services import SiteSettingsService
        from interactions.notifications.lang import owner_lang
        owner_id = SiteSettingsService.get().telegram_owner_id
        if owner_id:
            if register_owner_commands(api, owner_id, owner_lang()):
                self.stdout.write(self.style.SUCCESS(
                    f'Owner chat scope: {len(COMMAND_ORDER)} admin commands'
                ))
            else:
                self.stderr.write(self.style.ERROR('Owner chat-scope registration failed'))
        else:
            self.stderr.write(self.style.WARNING('telegram_owner_id not set — owner menu skipped'))

        # 3. Profile texts — compare-first (rate-limited API, deploy-safe).
        for getter, setter, field, key in _PROFILE_FIELDS:
            for code in ('', 'ru'):
                want = t(key, code or 'uz')
                get_payload = {'language_code': code} if code else {}
                current = api._post(getter, get_payload)
                have = (current or {}).get('result', {}).get(field, None)
                if have == want:
                    continue
                set_payload: dict = {field: want}
                if code:
                    set_payload['language_code'] = code
                result = api._post(setter, set_payload)
                if result and result.get('ok'):
                    self.stdout.write(self.style.SUCCESS(f'{setter} ({code or "default"}) updated'))
                else:
                    # 429 on setMyName is expected if changed too often — not fatal.
                    self.stderr.write(self.style.WARNING(f'{setter} ({code or "default"}): {result}'))
