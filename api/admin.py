from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Fields shown in the user list
    list_display = ('id', 'email', 'mobile_no', 'first_name', 'last_name', 'role', 'is_staff')
    search_fields = ('email', 'mobile_no', 'first_name', 'last_name')
    readonly_fields = ('date_joined',)

    # Fields grouping for editing a user
    fieldsets = (
        (None, {'fields': ('mobile_no', 'email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'profile_photo', 'role')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('date_joined', 'last_login')}),
    )

    # Fields used when creating a new user from admin panel
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile_no', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )

    ordering = ('id',)
