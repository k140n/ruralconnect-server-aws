"""Platform admin portal views."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from marketplace.models import (
    Product, Category, Banner, Campaign, CampaignProduct,
    BoostPlan, Boost, HeroSlide, SellerCtaBanner, sync_expired_boosts
)
from accounts.models import SellerProfile


from django.urls import reverse
from django.contrib.auth import login as auth_login
from accounts.forms import EmailLoginForm
from accounts.models import User
from ruralconnect_backend.security_utils import get_safe_redirect_url


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('platform_admin:login')}?next={request.path}")
        if not request.user.is_platform_admin:
            messages.error(request, 'Platform admin access required.')
            return redirect('marketplace:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_platform_admin:
            return redirect('platform_admin:dashboard')
        messages.error(request, 'You do not have platform administrator access.')
        return redirect('marketplace:home')

    form = EmailLoginForm()
    error = None

    if request.method == 'POST':
        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == User.ROLE_ADMIN:
                auth_login(request, user)
                next_url = request.GET.get('next') or request.POST.get('next')
                return redirect(get_safe_redirect_url(request, next_url, reverse('platform_admin:dashboard')))
            else:
                error = 'Access restricted: Only platform administrators can sign in here.'
        else:
            error = 'Invalid admin email or password.'

    return render(request, 'platform_admin/login.html', {
        'form': form,
        'error': error,
    })


@admin_required
def dashboard(request):
    total_products = Product.objects.count()
    approved = Product.objects.filter(status=Product.STATUS_APPROVED).count()
    paused = Product.objects.filter(status=Product.STATUS_PAUSED).count()
    suspended = Product.objects.filter(
        status__in=[Product.STATUS_SUSPENDED, Product.STATUS_REJECTED]
    ).count()
    sellers = SellerProfile.objects.count()
    from django.utils import timezone
    today = timezone.now().date()
    sync_expired_boosts()
    active_campaigns = Campaign.objects.filter(
        is_active=True, start_date__lte=today, end_date__gte=today
    ).count()
    active_promos = Product.objects.filter(promoted=True, status=Product.STATUS_APPROVED).count()

    recent_products = Product.objects.select_related('seller', 'category').order_by('-added')[:6]
    seller_list = SellerProfile.objects.select_related('user').annotate(
        product_count=Count('products')
    ).order_by('-product_count')
    pending_verifications_count = SellerProfile.objects.filter(verification_status=SellerProfile.STATUS_PENDING).count()

    return render(request, 'platform_admin/dashboard.html', {
        'total_products': total_products,
        'approved': approved,
        'paused': paused,
        'suspended': suspended,
        'rejected_suspended': suspended,
        'sellers': sellers,
        'pending_verifications_count': pending_verifications_count,
        'active_campaigns': active_campaigns,
        'active_promos': active_promos,
        'recent_products': recent_products,
        'seller_list': seller_list,
    })


@admin_required
def pending_products(request):
    """Direct publishing is enabled. Redirect to manage products."""
    messages.info(request, 'Instant publishing is enabled. Products go live directly without admin pre-approval.')
    return redirect('platform_admin:manage_products')


@admin_required
def approve_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.status = Product.STATUS_APPROVED
    product.needs_reapproval = False
    product.save()
    messages.success(request, f'"{product.name}" is active.')
    return redirect('platform_admin:manage_products')


@admin_required
def reject_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.status = Product.STATUS_SUSPENDED
    product.save()
    messages.warning(request, f'"{product.name}" has been suspended.')
    return redirect('platform_admin:manage_products')


@admin_required
def manage_products(request):
    products = Product.objects.select_related('seller', 'category')
    status_filter = request.GET.get('status', '').strip()
    promoted_filter = request.GET.get('promoted', '').strip()
    category_filter = request.GET.get('category', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()
    q = request.GET.get('q', '').strip()

    if status_filter == 'rejected_suspended':
        products = products.filter(status__in=[Product.STATUS_REJECTED, Product.STATUS_SUSPENDED])
    elif status_filter:
        products = products.filter(status=status_filter)

    if promoted_filter:
        products = products.filter(promoted=True)

    if category_filter:
        products = products.filter(category__slug=category_filter)

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(seller__business_name__icontains=q) |
            Q(category__name__icontains=q) |
            Q(location__icontains=q)
        )

    # Sorting options
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'stock_low':
        products = products.order_by('stock')
    elif sort_by == 'stock_out':
        products = products.filter(stock=0).order_by('-added')
    else:  # 'newest'
        products = products.order_by('-added')

    categories = Category.objects.all().order_by('name')
    has_active_filters = bool(q or status_filter or promoted_filter or category_filter or (sort_by and sort_by != 'newest'))

    return render(request, 'platform_admin/manage_products.html', {
        'products': products,
        'status_filter': status_filter,
        'promoted_filter': promoted_filter,
        'category_filter': category_filter,
        'sort_by': sort_by,
        'categories': categories,
        'has_active_filters': has_active_filters,
        'q': q,
        'total_count': Product.objects.count(),
        'STATUS_CHOICES': Product.STATUS_CHOICES,
    })


@admin_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" was permanently deleted.')
    return redirect('platform_admin:manage_products')


@admin_required
def change_product_status(request, pk):
    product = get_object_or_404(Product, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Product.STATUS_CHOICES):
        product.status = new_status
        if new_status == Product.STATUS_APPROVED:
            product.promoted = False if new_status == Product.STATUS_SUSPENDED else product.promoted
        product.save()
        messages.success(request, f'"{product.name}" status changed to {new_status}.')
    return redirect('platform_admin:manage_products')


@admin_required
def toggle_seller_suspension(request, pk):
    seller = get_object_or_404(SellerProfile, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'suspend':
            seller.user.is_active = False
            seller.user.save(update_fields=['is_active'])
            affected = Product.objects.filter(seller=seller).exclude(status=Product.STATUS_REJECTED).update(status=Product.STATUS_SUSPENDED)
            messages.warning(
                request,
                f'Seller "{seller.business_name}" has been suspended for malpractice. Account locked and {affected} product listing(s) removed from live storefront.'
            )
        elif action == 'restore':
            seller.user.is_active = True
            seller.user.save(update_fields=['is_active'])
            affected = Product.objects.filter(seller=seller, status=Product.STATUS_SUSPENDED).update(status=Product.STATUS_APPROVED)
            messages.success(
                request,
                f'Seller "{seller.business_name}" has been restored. Account unlocked and {affected} product listing(s) reactivated.'
            )
    return redirect(f"{reverse('platform_admin:dashboard')}?open_sellers=1")


@admin_required
def delete_seller(request, pk):
    seller = get_object_or_404(SellerProfile, pk=pk)
    if request.method == 'POST':
        b_name = seller.business_name
        if seller.order_items.exists():
            messages.error(
                request,
                f'Cannot permanently delete seller "{b_name}" because existing customer order history is attached to them. Please use "Suspend Seller" instead to lock the account while preserving financial and order records.'
            )
        else:
            user = seller.user
            user.delete()
            messages.success(request, f'Seller "{b_name}" and all catalog listings were permanently removed from the platform.')
    return redirect(f"{reverse('platform_admin:dashboard')}?open_sellers=1")


@admin_required
def review_seller_verification(request, pk):
    """Review and approve or reject seller KYC / artisan credentials."""
    seller = get_object_or_404(SellerProfile, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        from django.utils import timezone
        if action == 'approve':
            seller.is_verified = True
            seller.verification_status = SellerProfile.STATUS_VERIFIED
            seller.verification_reviewed_at = timezone.now()
            seller.verification_rejection_reason = ''
            seller.save()
            messages.success(
                request,
                f'Artisan credentials for "{seller.business_name}" have been approved! The "Verified Artisan" trust badge is now live on their storefront and products.'
            )
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                reason = 'Submitted document could not be authenticated. Please submit a valid, clear government artisan ID or certificate.'
            seller.is_verified = False
            seller.verification_status = SellerProfile.STATUS_REJECTED
            seller.verification_reviewed_at = timezone.now()
            seller.verification_rejection_reason = reason
            seller.save()
            messages.warning(
                request,
                f'Verification submission for "{seller.business_name}" was rejected. Feedback note was sent to the artisan.'
            )
        elif action == 'revoke':
            seller.is_verified = False
            seller.verification_status = SellerProfile.STATUS_UNSUBMITTED
            seller.save()
            messages.info(request, f'Verified badge for "{seller.business_name}" was revoked.')
    return redirect(f"{reverse('platform_admin:dashboard')}?open_sellers=1")


@admin_required
def manage_categories(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip().lower()
            emoji = request.POST.get('emoji', '🛒').strip()
            hue_raw = request.POST.get('hue', 200)
            try:
                hue = int(hue_raw) % 361
            except (ValueError, TypeError):
                hue = 200

            if name and slug:
                if Category.objects.filter(slug=slug).exists():
                    messages.error(request, f'A category with slug "{slug}" already exists.')
                else:
                    Category.objects.create(name=name, slug=slug, emoji=emoji, hue=hue)
                    messages.success(request, f'Category "{name}" {emoji} created successfully.')
            else:
                messages.error(request, 'Category name and slug are required.')

        elif action == 'edit':
            cat_id = request.POST.get('cat_id')
            cat = get_object_or_404(Category, pk=cat_id)
            name = request.POST.get('name', '').strip()
            slug = request.POST.get('slug', '').strip().lower()
            emoji = request.POST.get('emoji', '🛒').strip()
            hue_raw = request.POST.get('hue', 200)
            try:
                hue = int(hue_raw) % 361
            except (ValueError, TypeError):
                hue = 200

            if name and slug:
                # Check slug uniqueness if changed
                if slug != cat.slug and Category.objects.filter(slug=slug).exclude(pk=cat.pk).exists():
                    messages.error(request, f'Slug "{slug}" is already used by another category.')
                else:
                    cat.name = name
                    cat.slug = slug
                    cat.emoji = emoji
                    cat.hue = hue
                    cat.save()
                    messages.success(request, f'Category "{cat.name}" updated successfully.')
            else:
                messages.error(request, 'Category name and slug are required.')

        elif action == 'delete':
            cat_id = request.POST.get('cat_id')
            cat = get_object_or_404(Category, pk=cat_id)
            if cat.products.exists():
                messages.error(request, f'Cannot delete "{cat.name}": it contains {cat.products.count()} products.')
            else:
                cat.delete()
                messages.success(request, f'Category "{cat.name}" deleted.')

        return redirect('platform_admin:manage_categories')

    categories = Category.objects.annotate(product_count=Count('products')).order_by('name')
    total_categories = categories.count()
    total_products = Product.objects.count()
    top_category = Category.objects.annotate(product_count=Count('products')).order_by('-product_count').first()

    return render(request, 'platform_admin/manage_categories.html', {
        'categories': categories,
        'total_categories': total_categories,
        'total_products': total_products,
        'top_category': top_category,
    })


@admin_required
def banners(request):
    banner_list = Banner.objects.all().order_by('order', '-created_at')
    hero_slides = HeroSlide.objects.all().order_by('order', '-created_at')
    categories = Category.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        # ---- Top Hero Carousel Slide Actions ----
        if action == 'add_hero_slide':
            slide = HeroSlide(
                title=request.POST.get('title', '').strip(),
                accent_text=request.POST.get('accent_text', '').strip(),
                subtitle=request.POST.get('subtitle', '').strip(),
                button_text=request.POST.get('button_text', 'Explore crafts').strip(),
                button_link=request.POST.get('button_link', '/products/').strip(),
                icon=request.POST.get('icon', 'bi-lamp').strip(),
                bg_color=request.POST.get('bg_color', '#2b2b2b').strip(),
                order=int(request.POST.get('order', 0) or 0),
            )
            if 'image' in request.FILES:
                slide.image = request.FILES['image']
            slide.save()
            messages.success(request, f'Top hero slide "{slide.title}" created successfully.')
            return redirect('platform_admin:banners')

        elif action == 'edit_hero_slide':
            slide = get_object_or_404(HeroSlide, pk=request.POST.get('slide_id'))
            slide.title = request.POST.get('title', '').strip()
            slide.accent_text = request.POST.get('accent_text', '').strip()
            slide.subtitle = request.POST.get('subtitle', '').strip()
            slide.button_text = request.POST.get('button_text', 'Explore crafts').strip()
            slide.button_link = request.POST.get('button_link', '/products/').strip()
            slide.icon = request.POST.get('icon', 'bi-lamp').strip()
            slide.bg_color = request.POST.get('bg_color', '#2b2b2b').strip()
            try:
                slide.order = int(request.POST.get('order', 0) or 0)
            except (ValueError, TypeError):
                pass
            if 'image' in request.FILES:
                slide.image = request.FILES['image']
            elif request.POST.get('clear_image') == '1':
                slide.image = None
            slide.save()
            messages.success(request, f'Top hero slide "{slide.title}" updated successfully.')
            return redirect('platform_admin:banners')

        elif action == 'toggle_hero_slide':
            slide = get_object_or_404(HeroSlide, pk=request.POST.get('slide_id'))
            slide.is_active = not slide.is_active
            slide.save()
            status_text = 'activated' if slide.is_active else 'deactivated'
            messages.success(request, f'Top hero slide "{slide.title}" {status_text}.')
            return redirect('platform_admin:banners')

        elif action == 'delete_hero_slide':
            slide = get_object_or_404(HeroSlide, pk=request.POST.get('slide_id'))
            title = slide.title
            slide.delete()
            messages.success(request, f'Top hero slide "{title}" deleted.')
            return redirect('platform_admin:banners')

        # ---- Secondary Promotional Banner Actions ----
        elif action == 'add':
            new_banner = Banner(
                title=request.POST.get('title', '').strip(),
                subtitle=request.POST.get('subtitle', '').strip(),
                link_url=request.POST.get('link_url', '').strip(),
                css_class=request.POST.get('css_class', 'b1'),
                icon=request.POST.get('icon', '').strip(),
                order=int(request.POST.get('order', 0) or 0),
            )
            if 'image' in request.FILES:
                new_banner.image = request.FILES['image']
            new_banner.save()
            messages.success(request, 'Banner created successfully.')
        elif action == 'edit':
            banner = get_object_or_404(Banner, pk=request.POST.get('banner_id'))
            banner.title = request.POST.get('title', '').strip()
            banner.subtitle = request.POST.get('subtitle', '').strip()
            banner.link_url = request.POST.get('link_url', '').strip()
            banner.css_class = request.POST.get('css_class', 'b1')
            banner.icon = request.POST.get('icon', '').strip()
            try:
                banner.order = int(request.POST.get('order', 0) or 0)
            except (ValueError, TypeError):
                pass
            if 'image' in request.FILES:
                banner.image = request.FILES['image']
            elif request.POST.get('clear_image') == '1':
                banner.image = None
            banner.save()
            messages.success(request, f'Banner "{banner.title}" updated successfully.')
        elif action == 'toggle':
            banner = get_object_or_404(Banner, pk=request.POST.get('banner_id'))
            banner.is_active = not banner.is_active
            banner.save()
            status_text = 'activated' if banner.is_active else 'deactivated'
            messages.success(request, f'Banner "{banner.title}" {status_text}.')
        elif action == 'delete':
            b = get_object_or_404(Banner, pk=request.POST.get('banner_id'))
            title = b.title
            b.delete()
            messages.success(request, f'Banner "{title}" deleted.')

        # ---- Seller Call-To-Action Ad Banner Actions ----
        elif action == 'save_seller_cta':
            seller_cta, _ = SellerCtaBanner.objects.get_or_create(id=1)
            seller_cta.badge_text = request.POST.get('badge_text', 'Sponsored').strip()
            seller_cta.title = request.POST.get('title', '').strip()
            seller_cta.subtitle = request.POST.get('subtitle', '').strip()
            seller_cta.button_text = request.POST.get('button_text', 'Start selling').strip()
            seller_cta.button_link = request.POST.get('button_link', '/register/').strip()
            seller_cta.is_active = (request.POST.get('is_active') == '1')
            seller_cta.save()
            messages.success(request, 'Seller Call-To-Action Ad Banner updated successfully.')
            return redirect('platform_admin:banners')

        elif action == 'toggle_seller_cta':
            seller_cta, _ = SellerCtaBanner.objects.get_or_create(id=1)
            seller_cta.is_active = not seller_cta.is_active
            seller_cta.save()
            status_text = 'activated' if seller_cta.is_active else 'deactivated'
            messages.success(request, f'Seller Call-To-Action Ad Banner {status_text}.')
            return redirect('platform_admin:banners')

        return redirect('platform_admin:banners')

    seller_cta = SellerCtaBanner.objects.first()

    return render(request, 'platform_admin/banners.html', {
        'banners': banner_list,
        'hero_slides': hero_slides,
        'categories': categories,
        'seller_cta': seller_cta,
    })


@admin_required
def campaigns(request):
    from django.utils import timezone
    today = timezone.now().date()

    campaign_list = list(Campaign.objects.prefetch_related(
        'campaign_products__product__seller',
        'campaign_products__product__category'
    ).order_by('-start_date'))
    all_products = Product.objects.filter(status=Product.STATUS_APPROVED).select_related('seller', 'category').order_by('name')
    categories = Category.objects.all().order_by('name')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            try:
                discount_percent = int(request.POST.get('discount_percent', 0))
            except (ValueError, TypeError):
                discount_percent = 0
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            allow_seller_enrollment = (request.POST.get('allow_seller_enrollment') != '0')
            c = Campaign.objects.create(
                name=name,
                description=description,
                discount_percent=discount_percent,
                start_date=start_date,
                end_date=end_date,
                allow_seller_enrollment=allow_seller_enrollment,
            )
            # Bulk add products if selected in creation
            product_ids = request.POST.getlist('product_ids')
            for pid in product_ids:
                p = Product.objects.filter(pk=pid, status=Product.STATUS_APPROVED).first()
                if p:
                    CampaignProduct.objects.get_or_create(campaign=c, product=p)
            messages.success(request, f'Campaign "{c.name}" launched successfully.')
        elif action == 'edit':
            c = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            c.name = request.POST.get('name', '').strip()
            c.description = request.POST.get('description', '').strip()
            try:
                c.discount_percent = int(request.POST.get('discount_percent', c.discount_percent))
            except (ValueError, TypeError):
                pass
            if request.POST.get('start_date'):
                c.start_date = request.POST.get('start_date')
            if request.POST.get('end_date'):
                c.end_date = request.POST.get('end_date')
            if 'allow_seller_enrollment' in request.POST:
                c.allow_seller_enrollment = (request.POST.get('allow_seller_enrollment') == '1')
            c.save()
            messages.success(request, f'Campaign "{c.name}" updated successfully.')
        elif action == 'duplicate':
            orig = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            cloned = Campaign.objects.create(
                name=f"{orig.name} (Copy)",
                description=orig.description,
                discount_percent=orig.discount_percent,
                start_date=orig.start_date,
                end_date=orig.end_date,
                is_active=False
            )
            for cp in orig.campaign_products.all():
                CampaignProduct.objects.create(campaign=cloned, product=cp.product)
            messages.success(request, f'Campaign duplicated as "{cloned.name}".')
        elif action == 'add_product':
            campaign = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            product = get_object_or_404(Product, pk=request.POST.get('product_id'))
            CampaignProduct.objects.get_or_create(campaign=campaign, product=product)
            messages.success(request, f'"{product.name}" added to campaign.')
        elif action == 'add_products_bulk':
            campaign = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            product_ids = request.POST.getlist('product_ids')
            added_count = 0
            for pid in product_ids:
                p = Product.objects.filter(pk=pid, status=Product.STATUS_APPROVED).first()
                if p:
                    _, created = CampaignProduct.objects.get_or_create(campaign=campaign, product=p)
                    if created:
                        added_count += 1
            messages.success(request, f'Added {added_count} product(s) to "{campaign.name}".')
        elif action == 'remove_product':
            campaign = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            product = get_object_or_404(Product, pk=request.POST.get('product_id'))
            CampaignProduct.objects.filter(campaign=campaign, product=product).delete()
            messages.success(request, f'"{product.name}" removed from campaign "{campaign.name}".')
        elif action == 'toggle':
            c = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            c.is_active = not c.is_active
            c.save()
            state = "activated" if c.is_active else "paused"
            messages.success(request, f'Campaign "{c.name}" {state}.')
        elif action == 'delete':
            c = get_object_or_404(Campaign, pk=request.POST.get('campaign_id'))
            name = c.name
            c.delete()
            messages.success(request, f'Campaign "{name}" permanently deleted.')
        return redirect('platform_admin:campaigns')

    # Calculate metrics & timeline indicators for each campaign
    total_campaigns = len(campaign_list)
    live_campaigns_count = 0
    scheduled_campaigns_count = 0
    paused_campaigns_count = 0
    active_campaign_ids = []

    for c in campaign_list:
        total_days = max(1, (c.end_date - c.start_date).days)
        c.total_days = total_days
        
        # Product IDs already in this campaign for quick UI lookup
        c.enrolled_product_ids = set(c.campaign_products.values_list('product_id', flat=True))

        if not c.is_active:
            c.status_key = 'paused'
            paused_campaigns_count += 1
            c.progress_pct = 0
            c.days_left = 0
        elif today < c.start_date:
            c.status_key = 'scheduled'
            scheduled_campaigns_count += 1
            c.days_to_start = (c.start_date - today).days
            c.progress_pct = 0
            c.days_left = total_days
        elif today > c.end_date:
            c.status_key = 'ended'
            paused_campaigns_count += 1
            c.days_since_end = (today - c.end_date).days
            c.progress_pct = 100
            c.days_left = 0
        else:
            c.status_key = 'live'
            live_campaigns_count += 1
            active_campaign_ids.append(c.pk)
            days_passed = max(0, (today - c.start_date).days)
            c.progress_pct = min(100, max(0, round((days_passed / total_days) * 100)))
            c.days_left = max(0, (c.end_date - today).days)

    total_discounted_products = CampaignProduct.objects.filter(campaign_id__in=active_campaign_ids).values('product_id').distinct().count()

    active_camps = [c for c in campaign_list if c.status_key == 'live']
    if active_camps:
        avg_discount = round(sum(c.discount_percent for c in active_camps) / len(active_camps))
    elif campaign_list:
        avg_discount = round(sum(c.discount_percent for c in campaign_list) / len(campaign_list))
    else:
        avg_discount = 0

    return render(request, 'platform_admin/campaigns.html', {
        'campaigns': campaign_list,
        'all_products': all_products,
        'categories': categories,
        'total_campaigns': total_campaigns,
        'live_campaigns_count': live_campaigns_count,
        'scheduled_campaigns_count': scheduled_campaigns_count,
        'paused_campaigns_count': paused_campaigns_count,
        'total_discounted_products': total_discounted_products,
        'avg_discount': avg_discount,
        'today': today,
    })


@admin_required
def boost_plans(request):
    from django.utils import timezone
    today = timezone.now().date()

    # Automatically synchronize expired boosts and product promoted status
    sync_expired_boosts()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            BoostPlan.objects.create(
                name=request.POST.get('name', '').strip(),
                description=request.POST.get('description', '').strip(),
                price=request.POST.get('price', 0),
                duration_days=request.POST.get('duration_days', 7),
            )
            messages.success(request, 'Boost plan created successfully.')
        elif action == 'edit':
            plan = get_object_or_404(BoostPlan, pk=request.POST.get('plan_id'))
            plan.name = request.POST.get('name', '').strip()
            plan.description = request.POST.get('description', '').strip()
            try:
                plan.price = float(request.POST.get('price', plan.price))
                plan.duration_days = int(request.POST.get('duration_days', plan.duration_days))
            except (ValueError, TypeError):
                pass
            plan.save()
            messages.success(request, f'Boost plan "{plan.name}" updated successfully.')
        elif action == 'toggle':
            plan = get_object_or_404(BoostPlan, pk=request.POST.get('plan_id'))
            plan.is_active = not plan.is_active
            plan.save()
            status_text = 'activated' if plan.is_active else 'paused'
            messages.success(request, f'Boost plan "{plan.name}" {status_text}.')
        elif action == 'delete':
            plan = get_object_or_404(BoostPlan, pk=request.POST.get('plan_id'))
            if Boost.objects.filter(plan=plan, status=Boost.STATUS_ACTIVE, end_date__gte=today).exists():
                messages.error(request, f'Cannot delete "{plan.name}" because it has active seller boosts.')
            else:
                title = plan.name
                plan.delete()
                messages.success(request, f'Boost plan "{title}" deleted.')
        elif action == 'deactivate_boost':
            boost = get_object_or_404(Boost, pk=request.POST.get('boost_id'))
            boost.status = Boost.STATUS_CANCELLED
            boost.save()
            sync_expired_boosts()
            messages.success(request, f'Boost for "{boost.product.name}" cancelled.')
        return redirect('platform_admin:boost_plans')

    plans = list(BoostPlan.objects.all().order_by('price'))

    active_boosts = list(Boost.objects.filter(
        status=Boost.STATUS_ACTIVE,
        start_date__lte=today,
        end_date__gte=today
    ).select_related('product__seller', 'product__category', 'plan').order_by('end_date'))

    active_boost_ids = [b.id for b in active_boosts]
    past_boosts = list(Boost.objects.exclude(
        id__in=active_boost_ids
    ).select_related('product__seller', 'product__category', 'plan').order_by('-end_date')[:50])

    # Compute timeline metadata for active boosts
    for b in active_boosts:
        total_days = max(1, (b.end_date - b.start_date).days)
        days_passed = max(0, (today - b.start_date).days)
        days_remaining = max(0, (b.end_date - today).days)
        progress_pct = min(100, max(0, int((days_passed / total_days) * 100)))
        b.total_days = total_days
        b.days_passed = days_passed
        b.days_remaining = days_remaining
        b.progress_pct = progress_pct
        b.is_expiring_soon = days_remaining <= 3

    # Compute tier insights
    for p in plans:
        p.daily_rate = round(float(p.price) / p.duration_days, 1) if p.duration_days else float(p.price)
        p.active_count = sum(1 for b in active_boosts if b.plan_id == p.id)
        p.total_count = Boost.objects.filter(plan=p).count()

    # KPI Metrics
    all_boosts = Boost.objects.select_related('plan').all()
    total_boost_revenue = sum(float(b.plan.price) for b in all_boosts if b.plan)
    active_boost_revenue = sum(float(b.plan.price) for b in active_boosts if b.plan)

    active_sellers = set(b.product.seller_id for b in active_boosts if b.product and b.product.seller_id)
    all_sellers = set(b.product.seller_id for b in all_boosts if b.product and b.product.seller_id)

    active_plans_count = sum(1 for p in plans if p.is_active)

    past_expired_count = sum(1 for b in past_boosts if b.status != Boost.STATUS_CANCELLED)
    past_cancelled_count = sum(1 for b in past_boosts if b.status == Boost.STATUS_CANCELLED)

    return render(request, 'platform_admin/boost_plans.html', {
        'plans': plans,
        'active_boosts': active_boosts,
        'past_boosts': past_boosts,
        'today': today,
        'total_boost_revenue': total_boost_revenue,
        'active_boost_revenue': active_boost_revenue,
        'active_sellers_count': len(active_sellers),
        'total_sellers_count': len(all_sellers),
        'active_plans_count': active_plans_count,
        'past_expired_count': past_expired_count,
        'past_cancelled_count': past_cancelled_count,
    })
