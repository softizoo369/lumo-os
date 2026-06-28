from django.contrib import admin
from .models import User, Role, Feature, Permission

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'account_status', 'is_superuser')
    search_fields = ('email',)
    list_filter = ('account_status', 'is_superuser')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace', 'is_system_default')
    search_fields = ('name', 'workspace__name')