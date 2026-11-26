"""LiveBridge accounts: customers of the paid service, their connected apps, balance and purchases.

Customers are their own records keyed by the Google identity — not the site's staff `User` and not the
Telegram visitors (see the accounts design, "Who a customer is on the site"). Only token hashes are
stored. The ledger is append-only; every balance change goes through `livebridge.wallet`.
"""
from uuid import uuid4

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Account(models.Model):
    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)  # the id shown to Polar and the gateway
    google_sub = models.CharField(max_length=64, unique=True)
    email = models.EmailField()
    name = models.CharField(max_length=150, blank=True)
    balance_units = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    deletion_requested_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email


class Device(models.Model):
    """One connected copy of the app."""

    account = models.ForeignKey(Account, models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=64)
    name = models.CharField(max_length=80)
    access_hash = models.CharField(max_length=64, unique=True, null=True)
    access_expires_at = models.DateTimeField(null=True)
    refresh_hash = models.CharField(max_length=64, unique=True)
    refresh_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True)
    revoked_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.name


class RetiredRefreshToken(models.Model):
    """A refresh token that was rotated away. Presenting it again means a copied credential store: the device
    is signed out. Kept for as long as a refresh token can live."""

    device = models.ForeignKey(Device, models.CASCADE, related_name='retired_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)


class DeviceGrant(models.Model):
    """One "connect the app" attempt (shaped like the OAuth device grant)."""

    PENDING, APPROVED, DENIED, CONSUMED = 'pending', 'approved', 'denied', 'consumed'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (DENIED, 'Denied'), (CONSUMED, 'Consumed')]

    device_code_hash = models.CharField(max_length=64, unique=True)
    user_code = models.CharField(max_length=9, db_index=True)
    device_id = models.CharField(max_length=64)
    device_name = models.CharField(max_length=80)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    account = models.ForeignKey(Account, models.SET_NULL, null=True, blank=True)
    interval = models.PositiveSmallIntegerField(default=5)
    last_polled_at = models.DateTimeField(null=True)
    trial_outcome = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return self.user_code


class TrialDevice(models.Model):
    """A device that already gave someone a trial."""

    device_id = models.CharField(max_length=64, unique=True)
    account = models.ForeignKey(Account, models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.device_id


class Package(models.Model):
    code = models.SlugField(unique=True)
    price_cents = models.PositiveIntegerField()
    units = models.BigIntegerField()
    polar_product_id = models.CharField(max_length=64, blank=True)  # set in the admin per environment
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ('sort_order',)

    def __str__(self):
        return self.code


class LedgerEntry(models.Model):
    """Append-only. `units` is signed; `balance_after` is the account balance once it was applied."""

    TRIAL, PURCHASE, USAGE, REFUND, ADJUSTMENT = 'trial', 'purchase', 'usage', 'refund', 'adjustment'
    KIND_CHOICES = [(TRIAL, 'Free trial'), (PURCHASE, 'Purchase'), (USAGE, 'Usage'), (REFUND, 'Refund'),
                    (ADJUSTMENT, 'Adjustment')]

    # Kept, anonymised, if the account is deleted.
    account = models.ForeignKey(Account, models.SET_NULL, null=True, related_name='entries')
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    units = models.BigIntegerField()
    balance_after = models.BigIntegerField()
    reference = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name_plural = 'ledger entries'
        constraints = [
            models.UniqueConstraint(fields=['kind', 'reference'], condition=~Q(reference=''),
                                    name='livebridge_ledger_unique_reference'),
        ]

    def __str__(self):
        return f'{self.kind} {self.units:+d}'
