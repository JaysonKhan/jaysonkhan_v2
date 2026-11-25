"""Opt-in telemetry and feedback from the owner's open-source apps ("My Services").

Wire contract: LiveBridge repo `docs/telemetry-api.md` (v1). Numbers only — no text of what
was said, no raw IP addresses. Raw records are purged after 180 days
(`manage.py purge_service_telemetry`); installs and feedback are kept.
"""
from django.db import models
from django.utils import timezone

# The only app accepted today. The `app` column keeps the tables generic.
APP_LIVEBRIDGE = 'livebridge'
APPS = (APP_LIVEBRIDGE,)

UI_LANGUAGES = ('uz', 'ru', 'tr', 'en')

# Records without a turn store this in `turn_id` (and '' in `direction`), as the contract's
# de-duplication key says, so the UNIQUE constraint also covers them (NULLs never collide).
NO_TURN = 0


class AppInstall(models.Model):
    """One opted-in installation, identified by the random UUID v4 the app generated."""

    app = models.CharField(max_length=32, db_index=True)
    install_id = models.UUIDField()
    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)
    app_version = models.CharField(max_length=32, blank=True)
    os_version = models.CharField(max_length=64, blank=True)
    ui_language = models.CharField(max_length=8, blank=True)
    # Lifetime count of accepted `turn` records — survives the 180-day purge of raw records.
    turns_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Install'
        verbose_name_plural = 'Installs'
        ordering = ('-last_seen',)
        constraints = [
            models.UniqueConstraint(fields=('app', 'install_id'), name='apptelemetry_install_unique'),
        ]

    def __str__(self):
        return f'{self.app} {str(self.install_id)[:8]}'


class TelemetryRecord(models.Model):
    """One numbers-only record from an install's local log."""

    class Type(models.TextChoices):
        SESSION_START = 'session_start'
        TURN = 'turn'
        E2E = 'e2e'
        EMPTY_TURN = 'empty_turn'
        ERROR = 'error'
        RECONNECT = 'reconnect'
        RATING = 'rating'
        SESSION_END = 'session_end'

    install = models.ForeignKey(AppInstall, on_delete=models.CASCADE, related_name='records')
    type = models.CharField(max_length=16, choices=Type.choices)
    t = models.DateTimeField(help_text='Client clock (UTC).')
    received_at = models.DateTimeField(default=timezone.now, db_index=True)
    session = models.PositiveIntegerField()
    direction = models.CharField(max_length=3, blank=True)
    turn_id = models.IntegerField(default=NO_TURN)
    app_version = models.CharField(max_length=32, blank=True)

    # turn / e2e
    e2e_ms = models.PositiveIntegerField(null=True, blank=True)
    stt_commit_ms = models.PositiveIntegerField(null=True, blank=True)
    translate_first_ms = models.PositiveIntegerField(null=True, blank=True)
    translate_total_ms = models.PositiveIntegerField(null=True, blank=True)
    tts_first_audio_ms = models.PositiveIntegerField(null=True, blank=True)
    tts_total_ms = models.PositiveIntegerField(null=True, blank=True)
    audio_ms = models.PositiveIntegerField(null=True, blank=True)
    source_chars = models.PositiveIntegerField(null=True, blank=True)
    translation_chars = models.PositiveIntegerField(null=True, blank=True)
    model = models.CharField(max_length=64, blank=True)

    # error
    code = models.CharField(max_length=48, blank=True)
    fatal = models.BooleanField(null=True, blank=True)

    # rating
    rating = models.CharField(max_length=4, blank=True)

    # session_start
    mode = models.CharField(max_length=16, blank=True)
    # The owner's and the remote participant's language (2–3 letter codes). Rows stored before my_lang existed
    # have it empty, which means Uzbek.
    my_lang = models.CharField(max_length=3, blank=True)
    target_lang = models.CharField(max_length=3, blank=True)
    out_commit = models.CharField(max_length=16, blank=True)

    # session_end
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    turns = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Telemetry record'
        verbose_name_plural = 'Telemetry records'
        ordering = ('-t',)
        constraints = [
            # The client resends a batch after a network failure: a repeated record is ignored.
            models.UniqueConstraint(
                fields=('install', 'session', 'type', 'direction', 'turn_id', 't'),
                name='apptelemetry_record_dedup',
            ),
        ]
        indexes = [
            models.Index(fields=('type', 't'), name='apptelemetry_type_t'),
        ]

    def __str__(self):
        return f'{self.type} #{self.session}/{self.turn_id}'


class AppFeedback(models.Model):
    """A message a user wrote in the app's feedback form. Visible to the owner only."""

    app = models.CharField(max_length=32, db_index=True)
    install = models.ForeignKey(
        AppInstall, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback',
    )
    message = models.TextField(max_length=2000)
    email = models.EmailField(max_length=254, blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    app_version = models.CharField(max_length=32, blank=True)
    ui_language = models.CharField(max_length=8, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedback'
        ordering = ('-created_at',)

    def __str__(self):
        return self.message[:60]
