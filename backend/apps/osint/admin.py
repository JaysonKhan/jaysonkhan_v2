from django.contrib import admin

from unfold.admin import ModelAdmin

from osint.models import OsintAuditLog, OsintCache, OsintSearchLog


@admin.register(OsintCache)
class OsintCacheAdmin(ModelAdmin):
    list_display = ("endpoint_type", "target_id", "page", "fetched_at", "is_stale")
    list_filter = ("endpoint_type",)
    search_fields = ("target_id",)
    readonly_fields = ("data", "tech", "fetched_at", "fetched_by")

    @admin.display(boolean=True, description="Stale?")
    def is_stale(self, obj):
        return obj.is_stale


@admin.register(OsintSearchLog)
class OsintSearchLogAdmin(ModelAdmin):
    list_display = ("query", "query_type", "resolved_id", "searched_at", "api_cost")
    list_filter = ("query_type",)
    search_fields = ("query",)
    readonly_fields = ("searched_at",)


@admin.register(OsintAuditLog)
class OsintAuditLogAdmin(ModelAdmin):
    list_display = ("action", "endpoint_type", "target_id", "cached", "api_cost", "duration_ms", "performed_at")
    list_filter = ("action", "cached")
    search_fields = ("target_id",)
    readonly_fields = ("action", "endpoint_type", "target_id", "cached", "api_cost", "balance_after", "duration_ms", "error", "performed_by", "performed_at")
