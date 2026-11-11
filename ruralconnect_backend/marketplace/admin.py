from django.contrib import admin
from .models import (
    Category, Product, ProductImage, Review, Banner, Campaign,
    CampaignProduct, BoostPlan, Boost, CartItem, HeroSlide, Order, OrderItem,
    ProductDailyView, WhatsAppLead
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'emoji', 'order']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'seller', 'category', 'price', 'status', 'promoted', 'added']
    list_filter = ['status', 'category', 'promoted']
    search_fields = ['name', 'seller__business_name']
    list_editable = ['status', 'promoted']
    inlines = [ProductImageInline]
    readonly_fields = ['added', 'updated']
    actions = ['approve_products', 'reject_products', 'suspend_products']

    def approve_products(self, request, queryset):
        queryset.update(status=Product.STATUS_APPROVED, needs_reapproval=False)
    approve_products.short_description = 'Approve selected products'

    def reject_products(self, request, queryset):
        queryset.update(status=Product.STATUS_REJECTED)
    reject_products.short_description = 'Reject selected products'

    def suspend_products(self, request, queryset):
        queryset.update(status=Product.STATUS_SUSPENDED)
    suspend_products.short_description = 'Suspend selected products'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'reviewer', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved']
    list_editable = ['is_approved']


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'css_class', 'is_active', 'order']
    list_editable = ['is_active', 'order']


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ['title', 'accent_text', 'bg_color', 'is_active', 'order']
    list_editable = ['is_active', 'order']


class CampaignProductInline(admin.TabularInline):
    model = CampaignProduct
    extra = 1
    autocomplete_fields = ['product']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'discount_percent', 'start_date', 'end_date', 'allow_seller_enrollment', 'is_active']
    list_editable = ['is_active', 'allow_seller_enrollment']
    list_filter = ['is_active', 'allow_seller_enrollment']
    inlines = [CampaignProductInline]


@admin.register(BoostPlan)
class BoostPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'is_active']
    list_editable = ['is_active']


@admin.register(Boost)
class BoostAdmin(admin.ModelAdmin):
    list_display = ['product', 'plan', 'start_date', 'end_date', 'status']
    list_filter = ['status']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'session_key', 'quantity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'user__email', 'session_key']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'seller', 'product_name', 'unit_price', 'quantity', 'line_total']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'buyer', 'full_name', 'phone', 'total_amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_status', 'created_at']
    search_fields = ['order_number', 'buyer__email', 'full_name', 'phone']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at', 'updated_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product_name', 'seller', 'unit_price', 'quantity', 'line_total', 'status']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number', 'product_name', 'seller__business_name']


@admin.register(ProductDailyView)
class ProductDailyViewAdmin(admin.ModelAdmin):
    list_display = ['product', 'seller', 'date', 'views_count']
    list_filter = ['date']
    search_fields = ['product__name', 'seller__business_name']


@admin.register(WhatsAppLead)
class WhatsAppLeadAdmin(admin.ModelAdmin):
    list_display = ['product', 'seller', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'seller__business_name', 'user__email']


