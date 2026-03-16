from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UnfoldModelAdmin, UserAdmin):
    model = User
    list_display = ['username', 'email', 'is_staff', 'is_active', 'get_groups']
    search_fields = ['username', 'email']
    list_filter = ['is_staff', 'is_active', 'is_superuser', 'groups']
    filter_horizontal = ('groups', 'user_permissions')
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Info', {'fields': ('bio', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Info', {'fields': ('bio', 'profile_picture')}),
    )

    @admin.display(description='Groups')
    def get_groups(self, obj):
        return ', '.join(g.name for g in obj.groups.all()) or '—'
