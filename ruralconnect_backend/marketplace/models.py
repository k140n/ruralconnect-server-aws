"""
Core marketplace models: Category, Product, ProductImage, Review, Banner, Campaign, BoostPlan, Boost.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=10, default='🛒')
    hue = models.IntegerField(default=200, help_text='HSL hue for UI colour tint')
    icon = models.CharField(max_length=50, blank=True, help_text='Bootstrap icon class e.g. bi-tv')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'marketplace_category'
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_PAUSED = 'paused'
    STATUS_REJECTED = 'rejected'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CHOICES = [
        (STATUS_APPROVED, 'Active (Live)'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_SUSPENDED, 'Suspended'),
    ]

    name = models.CharField(max_length=250)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    seller = models.ForeignKey(
        'accounts.SellerProfile', on_delete=models.CASCADE, related_name='products'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seller_discount = models.PositiveIntegerField(default=0, help_text='Seller discount %')
    stock = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=300)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_APPROVED)
    reject_reason = models.TextField(blank=True)
    main_image = models.ImageField(upload_to='products/main/', blank=True, null=True)
    emoji = models.CharField(max_length=10, default='📦', help_text='Fallback emoji if no image')
    hue = models.IntegerField(default=200)
    promoted = models.BooleanField(default=False, help_text='Boost/sponsored listing')
    added = models.DateField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # Track if significant edits need re-approval
    needs_reapproval = models.BooleanField(default=False)

    class Meta:
        db_table = 'marketplace_product'
        ordering = ['-added']

    def __str__(self):
        return self.name

    # ---- Authoritative price logic (mirrors README formula) ----
    def effective_discount(self):
        """Returns the higher of seller discount or active campaign discount."""
        camp_disc = self.active_campaign_discount()
        return max(self.seller_discount, camp_disc)

    def active_campaign_discount(self):
        now = timezone.now().date()
        camp = (
            CampaignProduct.objects.filter(
                product=self,
                campaign__start_date__lte=now,
                campaign__end_date__gte=now,
                campaign__is_active=True,
            )
            .select_related('campaign')
            .first()
        )
        if camp:
            return camp.campaign.discount_percent
        return 0

    def final_price(self):
        disc = self.effective_discount()
        return round(self.price * (Decimal('1') - Decimal(disc) / Decimal('100')), 2)

    def average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0

    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    def is_public(self):
        return self.status == self.STATUS_APPROVED

    def is_new(self):
        """Returns True if the product was added within the last 14 days."""
        if not self.added:
            return False
        return (timezone.now().date() - self.added).days <= 14

    def origin_region(self):
        """Returns product origin region, defaulting to seller's origin."""
        seller_reg = self.seller.origin_region() if self.seller else ''
        if self.location:
            parts = [part.strip() for part in self.location.split(',') if part.strip()]
            if parts and parts[-1].lower() == 'india' and len(parts) > 1:
                return parts[-2]
            if len(parts) >= 2:
                return parts[-1]
            if parts:
                loc = parts[0]
                if seller_reg and loc.lower() != seller_reg.lower():
                    return f"{loc}, {seller_reg}"
                return loc
        return seller_reg or 'India'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('marketplace:product_detail', args=[self.pk])

    def get_whatsapp_inquiry_url(self, request=None):
        """Generates direct WhatsApp link with prefilled inquiry about this product."""
        import urllib.parse
        seller = self.seller
        number = seller.get_whatsapp_number()
        price_str = f"₹{self.final_price():.0f}"
        product_link = f"http://127.0.0.1:8002/products/{self.id}/"
        if request:
            product_link = request.build_absolute_uri(self.get_absolute_url())
        text = (
            f"Namaste {seller.business_name}! I am interested in *{self.name}* ({price_str}) "
            f"on RuralConnect ({product_link}). Could you please share more details on customization / delivery?"
        )
        return f"https://wa.me/{number}?text={urllib.parse.quote(text)}"


class ProductImage(models.Model):
    """Additional images for a product (up to 4 extra)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/extra/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'marketplace_product_image'
        ordering = ['order']

    def __str__(self):
        return f'Image for {self.product.name}'


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    text = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_review'
        # A user can only review a product once
        unique_together = [('product', 'reviewer')]
        ordering = ['-created_at']

    def __str__(self):
        return f'Review by {self.reviewer.full_name} on {self.product.name}'


class Banner(models.Model):
    """Homepage banners managed by platform admin."""
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    image = models.ImageField(upload_to='banners/', blank=True, null=True)
    css_class = models.CharField(max_length=20, default='b1', help_text='CSS class: b1, b2, b3, b4')
    icon = models.CharField(max_length=50, blank=True, help_text='Bootstrap icon class')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_banner'
        ordering = ['order']

    def __str__(self):
        return self.title


class HeroSlide(models.Model):
    """Top hero carousel slides on homepage, managed by platform admin."""
    title = models.CharField(max_length=200, help_text="Main heading e.g. 'Antique crafts made by village hands'")
    accent_text = models.CharField(max_length=150, blank=True, help_text="Emphasized text e.g. 'Up to 20% off'")
    subtitle = models.TextField(blank=True, help_text="Paragraph description below heading")
    button_text = models.CharField(max_length=100, default='Explore crafts')
    button_link = models.CharField(max_length=500, default='/products/')
    icon = models.CharField(max_length=50, default='bi-lamp', help_text="Bootstrap icon class e.g. bi-lamp, bi-tv")
    image = models.ImageField(upload_to='hero_slides/', blank=True, null=True, help_text="Optional custom artwork/image")
    bg_color = models.CharField(max_length=50, default='#2b2b2b', help_text="CSS background color e.g. #1f3d2f, #2b2b2b, #3b3b38")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_heroslide'
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title


class SellerCtaBanner(models.Model):
    """Middle 'Start Selling' ad band on homepage, managed by platform admin."""
    badge_text = models.CharField(max_length=50, default='Sponsored')
    title = models.CharField(max_length=250, default='Got an old radio, clock or craft at home?')
    subtitle = models.TextField(default='List it on RuralConnect. Free to join, publish and sell directly in minutes.')
    button_text = models.CharField(max_length=80, default='Start selling')
    button_link = models.CharField(max_length=500, default='/register/')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_seller_cta_banner'

    def __str__(self):
        return self.title


class Campaign(models.Model):
    """Platform-wide discount campaigns."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    discount_percent = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    allow_seller_enrollment = models.BooleanField(
        default=True,
        help_text='Allow sellers to self-enroll their approved products into this campaign'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_campaign'
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.name} ({self.discount_percent}% off)'

    def is_running(self):
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date

    def is_upcoming_or_running(self):
        today = timezone.now().date()
        return self.is_active and self.end_date >= today


class CampaignProduct(models.Model):
    """M2M through table linking campaigns to products."""
    ENROLLED_BY_ADMIN = 'admin'
    ENROLLED_BY_SELLER = 'seller'
    ENROLLED_BY_CHOICES = [
        (ENROLLED_BY_ADMIN, 'Platform Admin'),
        (ENROLLED_BY_SELLER, 'Artisan Seller'),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='campaign_products')
    enrolled_by = models.CharField(max_length=20, choices=ENROLLED_BY_CHOICES, default=ENROLLED_BY_ADMIN)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_campaign_product'
        unique_together = [('campaign', 'product')]


class BoostPlan(models.Model):
    """Boost plans that sellers can purchase (admin-managed)."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'marketplace_boost_plan'
        ordering = ['price']

    def __str__(self):
        return f'{self.name} – ₹{self.price} / {self.duration_days}d'


class BoostQuerySet(models.QuerySet):
    def active(self):
        today = timezone.now().date()
        return self.filter(status=Boost.STATUS_ACTIVE, start_date__lte=today, end_date__gte=today)

    def expired(self):
        today = timezone.now().date()
        return self.filter(models.Q(status=Boost.STATUS_EXPIRED) | (models.Q(status=Boost.STATUS_ACTIVE) & models.Q(end_date__lt=today)))


class Boost(models.Model):
    """Active boost on a specific product."""
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='boosts')
    plan = models.ForeignKey(BoostPlan, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = BoostQuerySet.as_manager()

    class Meta:
        db_table = 'marketplace_boost'
        ordering = ['-start_date']

    def __str__(self):
        return f'Boost: {self.product.name} ({self.status})'

    def is_active(self):
        today = timezone.now().date()
        return self.status == self.STATUS_ACTIVE and self.start_date <= today <= self.end_date


def sync_expired_boosts():
    """
    Finds all active boosts whose end_date has passed, marks them as 'expired',
    and resets Product.promoted=False if the product has no other live boost.
    Also clears promoted=False for any orphaned products.
    """
    today = timezone.now().date()

    # 1. Boosts currently marked active whose end_date is in the past
    past_active_boosts = Boost.objects.filter(status=Boost.STATUS_ACTIVE, end_date__lt=today)
    affected_product_ids = set(past_active_boosts.values_list('product_id', flat=True))

    if past_active_boosts.exists():
        past_active_boosts.update(status=Boost.STATUS_EXPIRED)

    # 2. Re-evaluate affected products
    for pid in affected_product_ids:
        has_active = Boost.objects.filter(
            product_id=pid,
            status=Boost.STATUS_ACTIVE,
            start_date__lte=today,
            end_date__gte=today
        ).exists()
        if not has_active:
            Product.objects.filter(pk=pid).update(promoted=False)

    # 3. Clean up any orphaned products marked promoted=True without an active boost
    valid_promoted_pids = Boost.objects.filter(
        status=Boost.STATUS_ACTIVE,
        start_date__lte=today,
        end_date__gte=today
    ).values_list('product_id', flat=True)
    Product.objects.filter(promoted=True).exclude(id__in=valid_promoted_pids).update(promoted=False)



class CartItem(models.Model):
    """Shopping cart item tied to an authenticated user or anonymous session."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_items',
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_cart_item'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                condition=models.Q(user__isnull=False),
                name='unique_user_cart_item'
            ),
            models.UniqueConstraint(
                fields=['session_key', 'product'],
                condition=models.Q(session_key__isnull=False, user__isnull=True),
                name='unique_session_cart_item'
            ),
        ]

    def __str__(self):
        owner = self.user.email if self.user else f'Session {self.session_key}'
        return f'{self.quantity}x {self.product.name} ({owner})'

    def total_price(self):
        return round(self.product.final_price() * self.quantity, 2)

    def total_mrp(self):
        return round(self.product.price * self.quantity, 2)


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAYMENT_COD = 'cod'
    PAYMENT_UPI = 'upi'
    PAYMENT_CHOICES = [
        (PAYMENT_COD, 'Cash on Delivery'),
        (PAYMENT_UPI, 'UPI / Online Payment'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')

    # Recipient & shipping details
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    shipping_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default='Kerala')
    postal_code = models.CharField(max_length=20)

    # Financial snapshots
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    discount_saved = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_COD)
    payment_status = models.CharField(max_length=20, default='pending')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    order_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_order'
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.order_number} ({self.buyer.email})"

    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    seller = models.ForeignKey('accounts.SellerProfile', on_delete=models.CASCADE, related_name='order_items')

    product_name = models.CharField(max_length=250)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    courier_name = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'marketplace_order_item'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quantity}x {self.product_name} (Seller: {self.seller.business_name})"

    def can_track(self):
        """Returns True if the item has a tracking number or is confirmed/shipped/delivered."""
        return bool(self.tracking_number) or self.status in [self.STATUS_CONFIRMED, self.STATUS_SHIPPED, self.STATUS_DELIVERED]

    def get_direct_tracking_url(self):
        """Generates direct tracking portal link."""
        from .tracking_services import get_direct_courier_url
        return get_direct_courier_url(self.courier_name, self.tracking_number)



class WishlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_wishlist_item'
        unique_together = [('user', 'product')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} -> {self.product.name}"


class ProductDailyView(models.Model):
    """Tracks daily page views for a product and seller."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='daily_views')
    seller = models.ForeignKey('accounts.SellerProfile', on_delete=models.CASCADE, related_name='product_views')
    date = models.DateField(default=timezone.now)
    views_count = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'marketplace_product_daily_view'
        unique_together = [('product', 'date')]
        indexes = [
            models.Index(fields=['seller', 'date']),
            models.Index(fields=['product', 'date']),
        ]

    def __str__(self):
        return f"{self.product.name} ({self.date}): {self.views_count} views"


class WhatsAppLead(models.Model):
    """Tracks clicks on WhatsApp inquiry button for a product and seller."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='whatsapp_leads')
    seller = models.ForeignKey('accounts.SellerProfile', on_delete=models.CASCADE, related_name='whatsapp_leads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_inquiries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketplace_whatsapp_lead'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'created_at']),
            models.Index(fields=['product', 'created_at']),
        ]

    def __str__(self):
        return f"WhatsApp lead for {self.product.name} ({self.created_at.strftime('%Y-%m-%d')})"



