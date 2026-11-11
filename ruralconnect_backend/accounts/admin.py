from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SellerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'full_name']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )
    readonly_fields = ['date_joined', 'last_login']


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'location', 'verification_status', 'verification_doc_type', 'is_verified', 'created_at']
    list_filter = ['verification_status', 'is_verified', 'verification_doc_type']
    search_fields = ['business_name', 'user__email', 'verification_id_number']
    readonly_fields = ['created_at', 'verification_submitted_at', 'verification_reviewed_at']
    fieldsets = (
        (None, {'fields': ('user', 'business_name', 'location', 'bio')}),
        ('Verification & Trust (KYC)', {
            'fields': (
                'is_verified',
                'verification_status',
                'verification_doc_type',
                'verification_id_number',
                'verification_document',
                'verification_rejection_reason',
                'verification_submitted_at',
                'verification_reviewed_at',
            )
        }),
        ('Dates', {'fields': ('created_at',)}),
    )
