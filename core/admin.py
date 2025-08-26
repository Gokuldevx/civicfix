from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Unregister default User model if it's registered
# admin.site.unregister(User)  # Only needed if User was previously registered

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'phone', 'is_citizen', 'is_staff')
    list_filter = ('is_citizen', 'is_moderator', 'is_resolver', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_citizen', 'is_moderator', 'is_resolver', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2'),
        }),
    )