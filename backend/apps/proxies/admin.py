"""Owner side of the proxy pool: the list, switching proxies on/off, and the TXT import page.

Every change made here republishes the shared file (``services.export_shared``) — that file is
what UzExam and EduStats read. The import page is an admin view, so it sits behind the staff
login and the admin IP allowlist like the rest of the panel.
"""
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path
from unfold.admin import ModelAdmin

from .models import Proxy
from .services import export_shared, import_proxies, pool_file


class ProxyImportForm(forms.Form):
    MAX_BYTES = 2 * 1024 * 1024

    file = forms.FileField(label='TXT fayl', required=False)
    text = forms.CharField(
        label="Yoki ro'yxatni shu yerga qo'ying", required=False,
        widget=forms.Textarea(attrs={
            'rows': 8, 'class': 'input-block', 'spellcheck': 'false',
            'placeholder': 'login:parol@1.2.3.4:3129',
        }),
    )
    replace = forms.BooleanField(label="Bu ro'yxatda yo'q proxylarni o'chirish", required=False)

    def clean(self):
        data = super().clean()
        upload = data.get('file')
        text = data.get('text') or ''
        if upload:
            if upload.size > self.MAX_BYTES:
                raise forms.ValidationError('Fayl juda katta (2 MB dan oshmasin).')
            text = upload.read().decode('utf-8', errors='replace') + '\n' + text
        if not text.strip():
            raise forms.ValidationError("TXT fayl tanlang yoki ro'yxatni matn sifatida qo'ying.")
        data['payload'] = text
        data['source'] = upload.name if upload else "qo'lda kiritilgan"
        return data


@admin.register(Proxy)
class ProxyAdmin(ModelAdmin):
    list_display = ('__str__', 'username', 'masked_password', 'is_active', 'source', 'created_at')
    list_filter = ('is_active', 'source')
    search_fields = ('host', 'username', 'source')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('activate', 'deactivate')

    @admin.display(description='Parol')
    def masked_password(self, obj):
        return f'{obj.password[:2]}•••' if obj.password else '—'

    def get_urls(self):
        return [
            path('import/', self.admin_site.admin_view(self.import_view), name='proxies_proxy_import'),
        ] + super().get_urls()

    def import_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        posted = request.method == 'POST'
        form = ProxyImportForm(request.POST, request.FILES) if posted else ProxyImportForm()
        if posted and form.is_valid():
            result = import_proxies(
                form.cleaned_data['payload'],
                source=form.cleaned_data['source'],
                replace=form.cleaned_data['replace'],
            )
            self._publish(request)
            self.message_user(
                request,
                f"Import tugadi: {result.created} ta yangi, {result.updated} ta paroli yangilandi, "
                f"{result.unchanged} ta o'zgarmadi, {result.removed} ta o'chirildi.",
                messages.SUCCESS,
            )
            if result.invalid_lines:
                shown = ', '.join(str(n) for n in result.invalid_lines[:10])
                more = '…' if len(result.invalid_lines) > 10 else ''
                self.message_user(
                    request,
                    f"{len(result.invalid_lines)} ta qator o'qilmadi (qator raqamlari: {shown}{more}).",
                    messages.WARNING,
                )
            return redirect('admin:proxies_proxy_changelist')
        context = {
            **self.admin_site.each_context(request),
            'title': 'Proxy import',
            'opts': self.model._meta,
            'form': form,
            'total_count': Proxy.objects.count(),
            'active_count': Proxy.objects.filter(is_active=True).count(),
            'pool_file': pool_file(),
        }
        return render(request, 'admin/proxies/import.html', context)

    def _publish(self, request):
        ok, error = export_shared()
        if not ok:
            self.message_user(
                request,
                f"Umumiy faylga yozib bo'lmadi — boshqa saytlar eski ro'yxatni ko'radi: {error}",
                messages.ERROR,
            )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._publish(request)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        self._publish(request)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        self._publish(request)

    @admin.action(description='Yoqish')
    def activate(self, request, queryset):
        self._switch(request, queryset, True)

    @admin.action(description="O'chirib qo'yish")
    def deactivate(self, request, queryset):
        self._switch(request, queryset, False)

    def _switch(self, request, queryset, active):
        count = queryset.update(is_active=active)
        self._publish(request)
        self.message_user(request, f"{count} ta proxy {'yoqildi' if active else 'o‘chirib qo‘yildi'}.")
