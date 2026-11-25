"""Outbound HTTP proxies managed by the owner and shared with the other sites on this server.

This site only stores and publishes the pool (see ``services.export_shared``); it never sends
traffic through it. HTTP proxies only: that is what the provider export contains, and the
readers in the other repos assume ``http://`` URLs.
"""
from urllib.parse import quote

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Proxy(models.Model):
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(65535)])
    username = models.CharField(max_length=128, blank=True)
    password = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(
        'Faol', default=True, db_index=True,
        help_text="O'chirilgan proxy umumiy faylga yozilmaydi — boshqa saytlar uni ishlatmaydi.",
    )
    source = models.CharField('Manba', max_length=150, blank=True, help_text='Import qilingan fayl nomi.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proxy'
        verbose_name_plural = 'Proxylar'
        ordering = ('host', 'port')
        constraints = [
            models.UniqueConstraint(fields=('host', 'port', 'username'), name='proxies_unique_endpoint'),
        ]

    def __str__(self):
        return f'{self.host}:{self.port}'

    @property
    def url(self) -> str:
        """``http://user:pass@host:port`` with the credentials percent-encoded."""
        auth = ''
        if self.username:
            auth = f"{quote(self.username, safe='')}:{quote(self.password, safe='')}@"
        return f'http://{auth}{self.host}:{self.port}'
