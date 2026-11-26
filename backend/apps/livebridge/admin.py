from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Account, Device, DeviceGrant, LedgerEntry, Package, TrialDevice

for _model in (Account, Device, DeviceGrant, TrialDevice, Package, LedgerEntry):
    admin.site.register(_model, ModelAdmin)
