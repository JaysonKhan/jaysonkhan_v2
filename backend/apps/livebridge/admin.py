"""Owner side of LiveBridge accounts: accounts (balance adjusted only with a reason), devices, a read-only
ledger, packages (Polar product ids are pasted here per environment)."""
from apptelemetry.admin import _ReadOnlyAdmin
from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action

from . import devices, wallet
from .models import Account, Device, DeviceGrant, LedgerEntry, Package, TrialDevice


class AdjustBalanceForm(forms.Form):
    units = forms.IntegerField(label="Birlik (musbat — qo'shish, manfiy — ayirish; 6000 = 1 daqiqa)")
    reason = forms.CharField(label='Sabab (majburiy)', max_length=200)

    def clean_units(self):
        if self.cleaned_data['units'] == 0:
            raise forms.ValidationError("0 bo'lmasin.")
        return self.cleaned_data['units']

    def clean_reason(self):
        reason = self.cleaned_data['reason'].strip()
        if not reason:
            raise forms.ValidationError('Sabab yozilsin.')
        return reason


class DeviceInline(TabularInline):
    model = Device
    extra = 0
    can_delete = False
    fields = ('name', 'device_id', 'created_at', 'last_used_at', 'revoked_at')
    readonly_fields = fields
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ('email', 'balance_minutes', 'created_at', 'last_seen_at', 'deletion_requested_at', 'is_active')
    list_filter = (('deletion_requested_at', admin.EmptyFieldListFilter), 'is_active')
    search_fields = ('email',)
    ordering = ('-created_at',)
    readonly_fields = ('public_id', 'google_sub', 'email', 'name', 'balance_units', 'balance_minutes', 'created_at',
                       'last_seen_at', 'deletion_requested_at')
    fields = readonly_fields + ('is_active',)
    inlines = (DeviceInline,)
    actions = ('sign_out_devices',)
    actions_detail = ('adjust_balance',)

    def has_add_permission(self, request):
        return False  # accounts are created by signing in with Google

    @admin.display(description='Balans (daqiqa)', ordering='balance_units')
    def balance_minutes(self, obj):
        return f'≈ {wallet.minutes(obj.balance_units)}'

    @admin.action(description="Barcha qurilmalarini hisobdan chiqarish")
    def sign_out_devices(self, request, queryset):
        count = 0
        for device in Device.objects.filter(account__in=queryset, revoked_at__isnull=True):
            devices.revoke(device)
            count += 1
        messages.success(request, f'{count} ta qurilma chiqarildi.')

    @action(description='Balansni tuzatish', url_path='adjust-balance', permissions=['change'])
    def adjust_balance(self, request, object_id):
        account = get_object_or_404(Account, pk=object_id)
        form = AdjustBalanceForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            entry = wallet.adjust(account, form.cleaned_data['units'], form.cleaned_data['reason'],
                                  by=request.user.email)
            messages.success(request, f'{entry.units:+d} birlik yozildi; balans {entry.balance_after}.')
            return redirect(reverse('admin:livebridge_account_change', args=[account.pk]))
        context = {**self.admin_site.each_context(request), 'title': 'Balansni tuzatish', 'opts': self.model._meta,
                   'account': account, 'form': form, 'minutes': wallet.minutes(account.balance_units)}
        return render(request, 'admin/livebridge/adjust_balance.html', context)


@admin.register(Device)
class DeviceAdmin(_ReadOnlyAdmin):
    list_display = ('name', 'account', 'created_at', 'last_used_at', 'revoked_at')
    list_filter = (('revoked_at', admin.EmptyFieldListFilter),)
    search_fields = ('name', 'account__email', 'device_id')
    list_select_related = ('account',)
    exclude = ('access_hash', 'refresh_hash')
    ordering = ('-created_at',)
    actions = ('sign_out',)

    @admin.action(description='Hisobdan chiqarish (sign out)')
    def sign_out(self, request, queryset):
        for device in queryset.filter(revoked_at__isnull=True):
            devices.revoke(device)
        messages.success(request, 'Tanlangan qurilmalar chiqarildi.')


@admin.register(LedgerEntry)
class LedgerEntryAdmin(_ReadOnlyAdmin):
    list_display = ('created_at', 'account', 'kind', 'units', 'balance_after', 'reference')
    list_filter = ('kind', 'created_at')
    search_fields = ('account__email', 'reference')
    list_select_related = ('account',)
    ordering = ('-created_at',)

    def has_delete_permission(self, request, obj=None):
        return False  # append-only: a wrong entry is corrected with an adjustment


@admin.register(DeviceGrant)
class DeviceGrantAdmin(_ReadOnlyAdmin):
    list_display = ('user_code', 'device_name', 'status', 'account', 'trial_outcome', 'created_at', 'expires_at')
    list_filter = ('status', 'trial_outcome')
    search_fields = ('user_code', 'device_name', 'account__email')
    exclude = ('device_code_hash',)
    ordering = ('-created_at',)


@admin.register(TrialDevice)
class TrialDeviceAdmin(_ReadOnlyAdmin):
    list_display = ('device_id', 'account', 'created_at')
    search_fields = ('device_id', 'account__email')
    ordering = ('-created_at',)


@admin.register(Package)
class PackageAdmin(ModelAdmin):
    list_display = ('code', 'price_cents', 'units', 'polar_product_id', 'is_active', 'sort_order')
    ordering = ('sort_order',)
