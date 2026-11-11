"""Custom User model with role support and Seller profile."""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_BUYER = 'buyer'
    ROLE_SELLER = 'seller'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_BUYER, 'Buyer'),
        (ROLE_SELLER, 'Seller'),
        (ROLE_ADMIN, 'Platform Admin'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_BUYER)
    phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'

    def __str__(self):
        return f'{self.full_name} <{self.email}>'

    @property
    def is_seller(self):
        return self.role == self.ROLE_SELLER

    @property
    def is_platform_admin(self):
        return self.role == self.ROLE_ADMIN


class SellerProfile(models.Model):
    """Extended profile for users with seller role."""

    # Verification status constants
    STATUS_UNSUBMITTED = 'unsubmitted'
    STATUS_PENDING = 'pending'
    STATUS_VERIFIED = 'verified'
    STATUS_REJECTED = 'rejected'

    VERIFICATION_STATUS_CHOICES = [
        (STATUS_UNSUBMITTED, 'Not Submitted'),
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_VERIFIED, 'Verified Artisan'),
        (STATUS_REJECTED, 'Needs Resubmission'),
    ]

    # Verification document types
    DOC_PEHCHAN = 'pehchan_card'
    DOC_HANDLOOM = 'handloom_board'
    DOC_SHG = 'shg_certificate'
    DOC_UDYAM = 'udyam_msme'
    DOC_GOVT_ID = 'govt_id'
    DOC_OTHER = 'other'

    DOC_TYPE_CHOICES = [
        (DOC_PEHCHAN, 'Pehchan Artisan ID Card (Ministry of Textiles)'),
        (DOC_HANDLOOM, 'State Handloom / Handicrafts Board Card'),
        (DOC_SHG, 'Self-Help Group (SHG) / Co-op Certificate'),
        (DOC_UDYAM, 'Udyam / MSME Artisan Registration'),
        (DOC_GOVT_ID, 'Government ID (Aadhaar / Voter ID / PAN)'),
        (DOC_OTHER, 'Other Recognized Craft / Workshop Certificate'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=200)
    location = models.CharField(max_length=300)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)

    # KYC / Artisan Verification Details
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default=STATUS_UNSUBMITTED,
    )
    verification_doc_type = models.CharField(
        max_length=40,
        choices=DOC_TYPE_CHOICES,
        blank=True,
    )
    verification_id_number = models.CharField(
        max_length=100,
        blank=True,
        help_text='Card number, Registration number, or ID reference',
    )
    verification_document = models.FileField(
        upload_to='seller_verifications/%Y/%m/',
        blank=True,
        null=True,
        help_text='Artisan ID card, certificate, or govt ID document (PDF/Image)',
    )
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_reviewed_at = models.DateTimeField(null=True, blank=True)
    verification_rejection_reason = models.TextField(
        blank=True,
        help_text='Reason provided to the seller if document is rejected',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seller_profile'

    def __str__(self):
        return self.business_name

    @property
    def is_verification_pending(self):
        return self.verification_status == self.STATUS_PENDING

    @property
    def is_verification_rejected(self):
        return self.verification_status == self.STATUS_REJECTED

    @property
    def has_submitted_document(self):
        return bool(self.verification_document) or self.verification_status != self.STATUS_UNSUBMITTED

    def average_rating(self):
        from marketplace.models import Review
        reviews = Review.objects.filter(product__seller=self)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0

    def total_reviews_count(self):
        from marketplace.models import Review
        return Review.objects.filter(product__seller=self).count()

    def get_active_subscription(self):
        from django.utils import timezone
        return self.subscriptions.filter(status='active', end_date__gte=timezone.now()).order_by('-end_date').first()

    def has_active_subscription(self):
        return self.get_active_subscription() is not None

    def get_whatsapp_number(self):
        """Returns clean international format phone number (e.g. 919847012345)."""
        phone = getattr(self.user, 'phone', '') if hasattr(self, 'user') else ''
        digits = ''.join(c for c in str(phone) if c.isdigit())
        if len(digits) == 10:
            return '91' + digits
        if len(digits) == 12 and digits.startswith('91'):
            return digits
        # Fallback to RuralConnect artisan support concierge
        return '919847012345'

    def get_whatsapp_url(self, prefill_text=None):
        """Generates direct WhatsApp click-to-chat URL."""
        import urllib.parse
        number = self.get_whatsapp_number()
        if not prefill_text:
            prefill_text = f"Namaste {self.business_name}, I am visiting your artisan studio on RuralConnect and would like to ask about your crafts."
        return f"https://wa.me/{number}?text={urllib.parse.quote(prefill_text)}"

    def origin_region(self):
        """Returns primary state/region extracted from workshop location (e.g. 'Kerala', 'Rajasthan')."""
        if not self.location:
            return 'India'
        parts = [p.strip() for p in self.location.split(',') if p.strip()]
        if parts and parts[-1].lower() == 'india' and len(parts) > 1:
            return parts[-2]
        if len(parts) >= 2:
            return parts[-1]
        return parts[0] if parts else 'India'



class BuyerProfile(models.Model):
    """Extended profile for buyers storing saved delivery and contact information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    shipping_address = models.TextField(blank=True, help_text='Street, house/flat name and number')
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, default='Kerala', blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'buyer_profile'

    def __str__(self):
        return f'BuyerProfile for {self.user.email}'


class DeliveryAddress(models.Model):
    """Multiple delivery addresses for buyers (e.g. Home, Work, Other)."""
    TYPE_HOME = 'home'
    TYPE_WORK = 'work'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_HOME, 'Home'),
        (TYPE_WORK, 'Work / Office'),
        (TYPE_OTHER, 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_addresses')
    full_name = models.CharField(max_length=150, help_text='Recipient name at this address')
    phone = models.CharField(max_length=15, help_text='10-digit mobile number for delivery')
    address_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_HOME)
    street_address = models.TextField(help_text='Flat/House No., Building Name, Street / Locality')
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default='Kerala')
    postal_code = models.CharField(max_length=10)
    landmark = models.CharField(max_length=200, blank=True)
    alt_phone = models.CharField(max_length=15, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'delivery_addresses'
        ordering = ['-is_default', '-updated_at']

    def __str__(self):
        return f"{self.full_name} ({self.get_address_type_display()}) - {self.city}, {self.postal_code}"

    def save(self, *args, **kwargs):
        # If this address is set as default, or if it's the user's first address, ensure it's default
        if self.is_default:
            DeliveryAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        elif not DeliveryAddress.objects.filter(user=self.user).exclude(pk=self.pk).exists():
            self.is_default = True

        super().save(*args, **kwargs)


class EmailVerificationOTP(models.Model):
    """Temporary 6-digit OTP codes for email verification during sign-up."""
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_verification_otps'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.email} ({'Verified' if self.is_verified else 'Pending'})"

    def is_valid(self):
        from django.utils import timezone
        return not self.is_verified and timezone.now() <= self.expires_at and self.attempts < 5

