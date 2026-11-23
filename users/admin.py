from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Quiz role', {'fields': ('role',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Quiz role', {'fields': ('role',)}),)
    list_display = ('username', 'email', 'role', 'is_staff')
