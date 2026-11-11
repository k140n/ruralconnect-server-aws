"""Models for Seller subscriptions and plans."""

from django.db import models
from django.utils import timezone


class SellerSubscriptionPlan(models.Model):
    PLAN_MONTHLY = 'monthly'
    PLAN_ANNUAL = 'annual'
    PLAN_CHOICES = [
        (PLAN_MONTHLY, 'Monthly'),
        (PLAN_ANNUAL, 'Annual'),
    ]

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=10, choices=PLAN_CHOICES, default=PLAN_MONTHLY)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30)
    max_products = models.PositiveIntegerField(default=0, help_text="0 for unlimited listings")
    features = models.TextField(blank=True, help_text="One perk/feature per line")
    badge_text = models.CharField(max_length=50, blank=True, help_text="e.g. Most Popular or Save 30%")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seller_subscription_plans'
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.name} – ₹{self.price} ({self.get_plan_type_display()})"

    @property
    def features_list(self):
        if not self.features:
            return []
        return [f.strip() for f in self.features.split('\n') if f.strip()]


class SellerSubscription(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    seller = models.ForeignKey('accounts.SellerProfile', on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SellerSubscriptionPlan, on_delete=models.CASCADE, related_name='seller_subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, default='Simulated Payment')
    payment_id = models.CharField(max_length=100, blank=True)
    auto_renew = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seller_subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.seller.business_name} – {self.plan.name} ({self.status})"

    def is_valid(self):
        return self.status == self.STATUS_ACTIVE and timezone.now() <= self.end_date

    @property
    def days_remaining(self):
        now = timezone.now()
        if now > self.end_date:
            return 0
        diff = self.end_date - now
        return max(0, diff.days)
