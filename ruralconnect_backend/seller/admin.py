from django.contrib import admin
from .models import SellerSubscriptionPlan, SellerSubscription


@admin.register(SellerSubscriptionPlan)
class SellerSubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'price', 'duration_days', 'max_products', 'badge_text', 'is_active', 'order']
    list_editable = ['price', 'is_active', 'order']
    list_filter = ['plan_type', 'is_active']
    search_fields = ['name']


@admin.register(SellerSubscription)
class SellerSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['seller', 'plan', 'status', 'start_date', 'end_date', 'amount_paid', 'days_remaining']
    list_filter = ['status', 'plan', 'created_at']
    search_fields = ['seller__business_name', 'seller__user__email', 'payment_id']
    raw_id_fields = ['seller']
