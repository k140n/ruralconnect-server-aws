"""Seller portal views."""

from decimal import Decimal
import csv
import json
import uuid
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.views.decorators.http import require_POST
from django.utils import timezone

from marketplace.models import (
    Product, Category, ProductImage, Review, Boost, BoostPlan,
    Campaign, CampaignProduct,
    Order, OrderItem, WishlistItem, ProductDailyView, WhatsAppLead,
    sync_expired_boosts
)
from accounts.models import SellerProfile
from ruralconnect_backend.security_utils import get_safe_redirect_url
from .forms import ProductForm, SellerProfileForm, SellerVerificationForm
from .models import SellerSubscriptionPlan, SellerSubscription


def seller_required(view_func):
    """Decorator: user must be authenticated, active, and have seller role."""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active:
            from django.contrib.auth import logout
            logout(request)
            messages.error(request, 'Your seller account has been suspended due to policy violations or malpractice. Please contact platform administration.')
            return redirect('accounts:login')
        if not request.user.is_seller:
            messages.error(request, 'Seller account required.')
            return redirect('marketplace:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@seller_required
def dashboard(request):
    seller = request.user.seller_profile
    products = Product.objects.filter(seller=seller)

    total = products.count()
    active = products.filter(status=Product.STATUS_APPROVED).count()
    paused = products.filter(status=Product.STATUS_PAUSED).count()
    out_of_stock = products.filter(stock=0).count()
    promos = products.filter(promoted=True).count()
    avg_rating = products.filter(
        reviews__is_approved=True
    ).aggregate(r=Avg('reviews__rating'))['r'] or 0

    # Orders & Revenue for this seller
    seller_order_items = OrderItem.objects.filter(seller=seller).select_related('order', 'order__buyer', 'product')
    total_orders = seller_order_items.count()
    pending_orders = seller_order_items.filter(status=OrderItem.STATUS_PENDING).count()
    shipped_orders = seller_order_items.filter(status=OrderItem.STATUS_SHIPPED).count()
    delivered_orders = seller_order_items.filter(status=OrderItem.STATUS_DELIVERED).count()
    total_revenue = seller_order_items.exclude(status=OrderItem.STATUS_CANCELLED).aggregate(
        total=Sum('line_total')
    )['total'] or 0
    recent_orders = seller_order_items.order_by('-created_at')[:8]

    # Detailed lists for instant access on dashboard and interactive modals
    all_products = products.select_related('category').order_by('-added')
    recent_products = all_products[:8]
    active_items = all_products.filter(status=Product.STATUS_APPROVED)
    paused_items = all_products.filter(status=Product.STATUS_PAUSED)
    sync_expired_boosts()
    today = timezone.now().date()
    promoted_items = all_products.filter(promoted=True)
    active_boosts = Boost.objects.filter(
        product__seller=seller,
        status=Boost.STATUS_ACTIVE,
        start_date__lte=today,
        end_date__gte=today
    ).select_related('product', 'plan')
    reviews = Review.objects.filter(
        product__seller=seller, is_approved=True
    ).select_related('product', 'reviewer').order_by('-created_at')[:15]

    return render(request, 'seller/dashboard.html', {
        'seller': seller,
        'total': total,
        'active': active,
        'approved': active,
        'paused': paused,
        'out_of_stock': out_of_stock,
        'promos': promos,
        'avg_rating': round(avg_rating, 1),
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
        'all_products': all_products,
        'recent_products': recent_products,
        'active_items': active_items,
        'approved_items': active_items,
        'paused_items': paused_items,
        'promoted_items': promoted_items,
        'active_boosts': active_boosts,
        'reviews': reviews,
        'active_subscription': seller.get_active_subscription(),
    })


@seller_required
def my_products(request):
    seller = request.user.seller_profile
    base_products = Product.objects.filter(seller=seller)
    products = base_products.select_related('category').order_by('-added')

    status_filter = request.GET.get('status', '').strip()
    q = request.GET.get('q', '').strip()

    if status_filter:
        products = products.filter(status=status_filter)
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(category__name__icontains=q) |
            Q(description__icontains=q)
        )

    all_count = base_products.count()
    active_count = base_products.filter(status=Product.STATUS_APPROVED).count()
    paused_count = base_products.filter(status=Product.STATUS_PAUSED).count()

    return render(request, 'seller/my_products.html', {
        'seller': seller,
        'products': products,
        'status_filter': status_filter,
        'q': q,
        'total_count': all_count,
        'active_count': active_count,
        'paused_count': paused_count,
        'STATUS_CHOICES': Product.STATUS_CHOICES,
    })


@seller_required
def add_product(request):
    seller = request.user.seller_profile

    # Subscription Gate: Seller must have an active subscription to list products
    if not seller.has_active_subscription():
        messages.warning(
            request, 
            "An active seller subscription plan is required to publish products on RuralConnect. Please choose a plan below to get started."
        )
        return redirect(f"{reverse('seller:subscription_plans')}?next={reverse('seller:add_product')}")

    active_sub = seller.get_active_subscription()
    if active_sub and active_sub.plan.max_products > 0:
        current_count = Product.objects.filter(seller=seller).count()
        if current_count >= active_sub.plan.max_products:
            messages.warning(
                request,
                f"You have reached your plan limit of {active_sub.plan.max_products} product listings. Upgrade to the Heritage Annual Pass for unlimited listings!"
            )
            return redirect('seller:subscription_plans')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = seller
            product.status = Product.STATUS_APPROVED  # Direct publishing (no admin approval required)
            product.needs_reapproval = False
            product.save()

            # Handle extra images (up to 4)
            extra_images = request.FILES.getlist('extra_images')
            for i, img in enumerate(extra_images[:4]):
                ProductImage.objects.create(product=product, image=img, order=i)

            messages.success(request, f'🎉 "{product.name}" is now live and published on RuralConnect!')
            return redirect('seller:my_products')
    else:
        form = ProductForm()

    categories = Category.objects.all()
    return render(request, 'seller/add_product.html', {'seller': seller, 'form': form, 'categories': categories})


@seller_required
def edit_product(request, pk):
    seller = request.user.seller_profile

    # Subscription Gate: Active plan required to edit products
    if not seller.has_active_subscription():
        messages.warning(
            request, 
            "An active seller subscription plan is required to edit and manage products. Please choose a plan below."
        )
        return redirect(f"{reverse('seller:subscription_plans')}?next={reverse('seller:edit_product', args=[pk])}")

    product = get_object_or_404(Product, pk=pk, seller=seller)


    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            # Handle newly uploaded additional gallery images
            extra_images = request.FILES.getlist('extra_images')
            if extra_images:
                current_order = product.images.count()
                for i, img in enumerate(extra_images):
                    ProductImage.objects.create(product=product, image=img, order=current_order + i)

            product = form.save(commit=False)
            # Maintain paused status if seller intentionally paused it, otherwise ensure it is live
            if product.status != Product.STATUS_PAUSED and product.status != Product.STATUS_SUSPENDED:
                product.status = Product.STATUS_APPROVED
            product.needs_reapproval = False
            product.save()

            messages.success(request, f'"{product.name}" updated successfully.')
            return redirect('seller:my_products')
    else:
        form = ProductForm(instance=product)

    return render(request, 'seller/edit_product.html', {
        'seller': seller, 'form': form, 'product': product
    })


@seller_required
@require_POST
def toggle_product_status(request, pk):
    """Toggle a seller's product between Active (Live) and Paused (Hidden)."""
    seller = request.user.seller_profile
    product = get_object_or_404(Product, pk=pk, seller=seller)

    if product.status == Product.STATUS_SUSPENDED:
        messages.error(request, 'This listing was suspended by platform administrators and cannot be toggled.')
        return redirect(request.META.get('HTTP_REFERER') or 'seller:my_products')

    if product.status == Product.STATUS_PAUSED:
        product.status = Product.STATUS_APPROVED
        product.save(update_fields=['status'])
        messages.success(request, f'"{product.name}" is now Active and visible on the marketplace.')
    else:
        product.status = Product.STATUS_PAUSED
        product.save(update_fields=['status'])
        messages.info(request, f'"{product.name}" is now Paused and hidden from buyers.')

    return redirect(request.META.get('HTTP_REFERER') or 'seller:my_products')


@seller_required
def delete_product_image(request, pk, image_id):
    """Delete a specific gallery photo for this product."""
    seller = request.user.seller_profile
    product = get_object_or_404(Product, pk=pk, seller=seller)
    img_obj = get_object_or_404(ProductImage, pk=image_id, product=product)
    if request.method == 'POST':
        if img_obj.image:
            img_obj.image.delete(save=False)
        img_obj.delete()
        messages.success(request, 'Gallery photo deleted successfully.')
    return redirect('seller:edit_product', pk=pk)


@seller_required
def delete_cover_image(request, pk):
    """Delete the main cover photo for this product."""
    seller = request.user.seller_profile
    product = get_object_or_404(Product, pk=pk, seller=seller)
    if request.method == 'POST':
        if product.main_image:
            product.main_image.delete(save=False)
            product.main_image = None
            product.save(update_fields=['main_image'])
            messages.success(request, 'Cover photo removed successfully.')
    return redirect('seller:edit_product', pk=pk)


@seller_required
def delete_product(request, pk):
    seller = request.user.seller_profile
    product = get_object_or_404(Product, pk=pk, seller=seller)
    if request.method == 'POST':
        product.delete()
        messages.success(request, f'"{product.name}" has been deleted.')
    return redirect('seller:my_products')


@seller_required
def promotions(request):
    seller = request.user.seller_profile
    sync_expired_boosts()
    today = timezone.now().date()

    # Approved products belonging to this seller
    approved_products = Product.objects.filter(seller=seller, status=Product.STATUS_APPROVED)
    boost_plans = BoostPlan.objects.filter(is_active=True)
    active_boosts = Boost.objects.filter(
        product__seller=seller,
        status=Boost.STATUS_ACTIVE,
        start_date__lte=today,
        end_date__gte=today
    ).select_related('product', 'plan')
    past_boosts = Boost.objects.filter(
        product__seller=seller
    ).exclude(
        id__in=active_boosts.values_list('id', flat=True)
    ).select_related('product', 'plan').order_by('-end_date')[:20]

    # Available platform campaigns open for seller participation
    raw_campaigns = Campaign.objects.filter(
        is_active=True,
        end_date__gte=today,
        allow_seller_enrollment=True
    ).order_by('end_date')

    # Enrolled campaign products belonging to this artisan
    enrolled_campaign_products = CampaignProduct.objects.filter(
        product__seller=seller
    ).select_related('campaign', 'product', 'product__category').order_by('-added_at')

    # Annotate campaigns with seller-specific counts and enrolled product IDs
    available_campaigns = []
    for c in raw_campaigns:
        c_enrolled_pids = set(
            enrolled_campaign_products.filter(campaign=c).values_list('product_id', flat=True)
        )
        c.seller_enrolled_pids = c_enrolled_pids
        c.seller_enrolled_count = len(c_enrolled_pids)
        c.is_live = (c.start_date <= today <= c.end_date)
        c.days_remaining = (c.end_date - today).days

        c_eligible = []
        for p in approved_products:
            festive_price = round(float(p.price) * (1 - c.discount_percent / 100), 2)
            c_eligible.append({
                'product': p,
                'is_enrolled': (p.id in c_enrolled_pids),
                'festive_price': festive_price,
            })
        c.eligible_products = c_eligible
        available_campaigns.append(c)

    for cp in enrolled_campaign_products:
        cp.festive_price = round(float(cp.product.price) * (1 - cp.campaign.discount_percent / 100), 2)
        cp.is_campaign_live = cp.campaign.is_running()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'enroll_campaign':
            campaign_id = request.POST.get('campaign_id')
            product_ids = request.POST.getlist('product_ids')
            campaign = get_object_or_404(Campaign, pk=campaign_id, is_active=True, allow_seller_enrollment=True)

            if campaign.end_date < today:
                messages.error(request, 'This campaign has already concluded.')
                return redirect('seller:promotions')

            if not product_ids:
                messages.warning(request, 'Please select at least one product to enroll in the campaign.')
                return redirect('seller:promotions')

            enrolled_count = 0
            for pid in product_ids:
                p = approved_products.filter(pk=pid).first()
                if p:
                    _, created = CampaignProduct.objects.get_or_create(
                        campaign=campaign,
                        product=p,
                        defaults={'enrolled_by': CampaignProduct.ENROLLED_BY_SELLER}
                    )
                    if created:
                        enrolled_count += 1

            if enrolled_count > 0:
                messages.success(
                    request,
                    f'🎉 Successfully enrolled {enrolled_count} product(s) into "{campaign.name}"! The flat {campaign.discount_percent}% campaign discount is now active.'
                )
            else:
                messages.info(request, 'Selected product(s) were already enrolled in this campaign.')
            return redirect('seller:promotions')

        elif action == 'withdraw_campaign':
            cp_id = request.POST.get('campaign_product_id')
            cp = get_object_or_404(CampaignProduct, pk=cp_id, product__seller=seller)
            p_name = cp.product.name
            c_name = cp.campaign.name
            cp.delete()
            messages.info(request, f'"{p_name}" has been withdrawn from the "{c_name}" campaign.')
            return redirect('seller:promotions')

        else:
            # Boost creation action
            product_id = request.POST.get('product_id')
            plan_id = request.POST.get('plan_id')
            try:
                product = approved_products.get(pk=product_id)
                plan = boost_plans.get(pk=plan_id)
                Boost.objects.create(
                    product=product,
                    plan=plan,
                    start_date=today,
                    end_date=today + timedelta(days=plan.duration_days),
                )
                product.promoted = True
                product.save(update_fields=['promoted'])
                messages.success(request, f'"{product.name}" is now boosted with "{plan.name}".')
            except (Product.DoesNotExist, BoostPlan.DoesNotExist):
                messages.error(request, 'Invalid product or boost plan.')
            return redirect('seller:promotions')

    return render(request, 'seller/promotions.html', {
        'seller': seller,
        'approved_products': approved_products,
        'boost_plans': boost_plans,
        'active_boosts': active_boosts,
        'past_boosts': past_boosts,
        'available_campaigns': available_campaigns,
        'enrolled_campaign_products': enrolled_campaign_products,
    })


@seller_required
def reviews(request):
    seller = request.user.seller_profile
    seller_reviews = Review.objects.filter(
        product__seller=seller, is_approved=True
    ).select_related('product', 'reviewer').order_by('-created_at')
    return render(request, 'seller/reviews.html', {'seller': seller, 'reviews': seller_reviews})


@seller_required
def profile(request):
    seller = request.user.seller_profile
    form = SellerProfileForm(instance=seller)
    kyc_form = SellerVerificationForm(instance=seller)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'submit_kyc':
            kyc_form = SellerVerificationForm(request.POST, request.FILES, instance=seller)
            if kyc_form.is_valid():
                kyc_seller = kyc_form.save(commit=False)
                kyc_seller.verification_status = SellerProfile.STATUS_PENDING
                kyc_seller.verification_submitted_at = timezone.now()
                kyc_seller.verification_rejection_reason = ''
                kyc_seller.save()
                messages.success(request, 'Your artisan verification documents have been submitted! Our team will review them within 24-48 hours.')
                return redirect(f"{reverse('seller:profile')}#kyc")
            else:
                messages.error(request, 'Please check the verification form below for errors.')
        else:
            form = SellerProfileForm(request.POST, instance=seller)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your seller profile and contact details have been updated successfully.')
                return redirect('seller:profile')

    total_products = seller.products.count()
    approved_products = seller.products.filter(status=Product.STATUS_APPROVED).count()
    avg_rating = seller.average_rating()
    review_count = seller.total_reviews_count()

    return render(request, 'seller/profile.html', {
        'seller': seller,
        'form': form,
        'kyc_form': kyc_form,
        'total_products': total_products,
        'approved_products': approved_products,
        'avg_rating': avg_rating,
        'review_count': review_count,
    })


@seller_required
def orders(request):
    """View and filter all incoming customer orders for this vendor."""
    seller = request.user.seller_profile
    order_items = OrderItem.objects.filter(seller=seller).select_related(
        'order', 'order__buyer', 'product'
    ).order_by('-created_at')

    status_filter = request.GET.get('status', '').strip()
    q = request.GET.get('q', '').strip()

    if status_filter:
        order_items = order_items.filter(status=status_filter)
    if q:
        order_items = order_items.filter(
            Q(order__order_number__icontains=q) |
            Q(product_name__icontains=q) |
            Q(order__full_name__icontains=q) |
            Q(order__phone__icontains=q) |
            Q(order__city__icontains=q)
        )

    base_items = OrderItem.objects.filter(seller=seller)
    total_count = base_items.count()
    pending_count = base_items.filter(status=OrderItem.STATUS_PENDING).count()
    confirmed_count = base_items.filter(status=OrderItem.STATUS_CONFIRMED).count()
    shipped_count = base_items.filter(status=OrderItem.STATUS_SHIPPED).count()
    delivered_count = base_items.filter(status=OrderItem.STATUS_DELIVERED).count()
    cancelled_count = base_items.filter(status=OrderItem.STATUS_CANCELLED).count()

    return render(request, 'seller/orders.html', {
        'seller': seller,
        'order_items': order_items,
        'status_filter': status_filter,
        'q': q,
        'total_count': total_count,
        'pending_count': pending_count,
        'confirmed_count': confirmed_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,
        'cancelled_count': cancelled_count,
        'STATUS_CHOICES': OrderItem.STATUS_CHOICES,
    })


@seller_required
def update_order_status(request, item_id):
    """Update shipment/fulfillment status for a vendor's ordered product."""
    seller = request.user.seller_profile
    item = get_object_or_404(OrderItem, id=item_id, seller=seller)

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        courier_name = request.POST.get('courier_name', '').strip()
        tracking_number = request.POST.get('tracking_number', '').strip()

        valid_statuses = [s[0] for s in OrderItem.STATUS_CHOICES]
        if new_status in valid_statuses:
            item.status = new_status
            if courier_name:
                item.courier_name = courier_name
            if tracking_number:
                item.tracking_number = tracking_number
            item.save()

            # Auto-update parent order status based on all items
            order = item.order
            all_statuses = set(order.items.values_list('status', flat=True))
            if all_statuses == {OrderItem.STATUS_DELIVERED}:
                order.status = Order.STATUS_COMPLETED
                order.save(update_fields=['status'])
            elif any(s in all_statuses for s in [OrderItem.STATUS_SHIPPED, OrderItem.STATUS_CONFIRMED]):
                order.status = Order.STATUS_PROCESSING
                order.save(update_fields=['status'])

            messages.success(request, f"Order #{order.order_number} ({item.product_name}) status set to {new_status.title()}.")
        else:
            messages.error(request, "Invalid order status value.")

    raw_next = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('seller:orders')
    return redirect(get_safe_redirect_url(request, raw_next, reverse('seller:orders')))


@seller_required
def subscription_plans(request):
    """View and compare subscription plans (Monthly vs Annual)."""
    seller = request.user.seller_profile
    plans = SellerSubscriptionPlan.objects.filter(is_active=True).order_by('order', 'price')
    current_sub = seller.get_active_subscription()
    next_url = request.GET.get('next', '')

    past_subscriptions = seller.subscriptions.all().order_by('-created_at')[:6]

    return render(request, 'seller/subscription_plans.html', {
        'seller': seller,
        'plans': plans,
        'current_sub': current_sub,
        'past_subscriptions': past_subscriptions,
        'next_url': next_url,
    })


@seller_required
def subscribe_checkout(request, plan_id):
    """Checkout and payment simulation for selected subscription plan."""
    seller = request.user.seller_profile
    plan = get_object_or_404(SellerSubscriptionPlan, pk=plan_id, is_active=True)
    current_sub = seller.get_active_subscription()
    next_url = request.GET.get('next') or request.POST.get('next', '')

    if request.method == 'POST':
        now = timezone.now()
        # If already subscribed and still active, extend end date
        if current_sub and current_sub.end_date > now:
            start_date = current_sub.start_date
            end_date = current_sub.end_date + timedelta(days=plan.duration_days)
        else:
            start_date = now
            end_date = now + timedelta(days=plan.duration_days)

        payment_method = request.POST.get('payment_method', 'Instant UPI / Card (Test Mode)')
        payment_ref = f"RC-SUB-{uuid.uuid4().hex[:8].upper()}"

        new_sub = SellerSubscription.objects.create(
            seller=seller,
            plan=plan,
            status=SellerSubscription.STATUS_ACTIVE,
            start_date=start_date,
            end_date=end_date,
            amount_paid=plan.price,
            payment_method=payment_method,
            payment_id=payment_ref,
            auto_renew=(request.POST.get('auto_renew') == 'on')
        )

        # Unpause any previously paused products
        Product.objects.filter(seller=seller, status=Product.STATUS_PAUSED).update(status=Product.STATUS_APPROVED)

        messages.success(
            request, 
            f"🎉 Congratulations! Your {plan.name} is now ACTIVE until {end_date.strftime('%d %B %Y')}. You can now list and sell products on RuralConnect!"
        )

        return redirect(get_safe_redirect_url(request, next_url, reverse('seller:add_product')))

    return render(request, 'seller/subscription_checkout.html', {
        'seller': seller,
        'plan': plan,
        'current_sub': current_sub,
        'next_url': next_url,
    })


@seller_required
@require_POST
def cancel_subscription(request):
    """Cancel auto-renew on active plan."""
    seller = request.user.seller_profile
    current_sub = seller.get_active_subscription()
    if current_sub:
        current_sub.auto_renew = False
        current_sub.save(update_fields=['auto_renew'])
        messages.info(request, "Auto-renewal has been turned off. Your plan remains active until the end of your billing period.")
    return redirect('seller:subscription_plans')


@seller_required
def analytics(request):
    """Dedicated analytics and performance dashboard for the logged-in seller."""
    seller = request.user.seller_profile
    range_param = request.GET.get('range', '30d')
    now = timezone.now()
    today = now.date()

    if range_param == '7d':
        start_datetime = now - timedelta(days=7)
        range_label = 'Last 7 Days'
        num_days = 7
    elif range_param == '90d':
        start_datetime = now - timedelta(days=90)
        range_label = 'Last 90 Days'
        num_days = 90
    elif range_param == 'year':
        start_datetime = timezone.datetime(now.year, 1, 1, tzinfo=timezone.get_current_timezone())
        range_label = f'Year {now.year}'
        num_days = None
    elif range_param == 'all':
        start_datetime = None
        range_label = 'All Time'
        num_days = None
    else:
        range_param = '30d'
        start_datetime = now - timedelta(days=30)
        range_label = 'Last 30 Days'
        num_days = 30

    # Base OrderItems query for this seller
    seller_order_items = OrderItem.objects.filter(seller=seller).select_related('order', 'product')
    seller_views = ProductDailyView.objects.filter(seller=seller)
    seller_leads = WhatsAppLead.objects.filter(seller=seller)
    seller_wishlists = WishlistItem.objects.filter(product__seller=seller)

    if start_datetime:
        period_items = seller_order_items.filter(created_at__gte=start_datetime)
        period_views = seller_views.filter(date__gte=start_datetime.date())
        period_leads = seller_leads.filter(created_at__gte=start_datetime)
        period_wishlists = seller_wishlists.filter(created_at__gte=start_datetime)
    else:
        period_items = seller_order_items
        period_views = seller_views
        period_leads = seller_leads
        period_wishlists = seller_wishlists

    total_views = period_views.aggregate(total=Sum('views_count'))['total'] or 0
    total_leads = period_leads.count()
    total_wishlists = period_wishlists.count()
    high_intent_count = total_leads + total_wishlists

    # Optional CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="ruralconnect_sales_{range_param}_{today.strftime("%Y%m%d")}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order #', 'Date', 'Product Name', 'Category', 'Unit Price (INR)', 'Quantity', 'Line Total (INR)', 'Item Status', 'Payment Method', 'City', 'State', 'Courier Name', 'Tracking #'])
        for item in period_items.order_by('-created_at'):
            writer.writerow([
                item.order.order_number if item.order else 'N/A',
                item.created_at.strftime('%Y-%m-%d %H:%M'),
                item.product_name,
                item.product.category.name if (item.product and item.product.category) else 'Handicrafts',
                item.unit_price,
                item.quantity,
                item.line_total,
                item.get_status_display(),
                item.order.get_payment_method_display() if item.order else 'N/A',
                item.order.city if item.order else 'N/A',
                item.order.state if item.order else 'N/A',
                item.courier_name or 'Rural Courier Network',
                item.tracking_number or 'N/A',
            ])
        return response

    valid_items = period_items.exclude(status=OrderItem.STATUS_CANCELLED)
    total_revenue = valid_items.aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')
    total_units = valid_items.aggregate(qty=Sum('quantity'))['qty'] or 0
    orders_count = period_items.values('order_id').distinct().count()
    cancelled_items = period_items.filter(status=OrderItem.STATUS_CANCELLED)
    cancelled_count = cancelled_items.count()
    cancelled_revenue = cancelled_items.aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')
    aov = round(total_revenue / orders_count, 2) if orders_count > 0 else Decimal('0.00')

    # Conversion Rate Metrics
    conversion_rate = round((orders_count / total_views * 100), 2) if total_views > 0 else 0.0
    intent_conversion_rate = round((orders_count / high_intent_count * 100), 1) if high_intent_count > 0 else 0.0

    # Status distribution
    status_counts = {
        'pending': period_items.filter(status=OrderItem.STATUS_PENDING).count(),
        'confirmed': period_items.filter(status=OrderItem.STATUS_CONFIRMED).count(),
        'shipped': period_items.filter(status=OrderItem.STATUS_SHIPPED).count(),
        'delivered': period_items.filter(status=OrderItem.STATUS_DELIVERED).count(),
        'cancelled': cancelled_count,
    }

    # Funnel breakdown
    funnel = {
        'views': total_views,
        'interest': high_intent_count,
        'wishlists': total_wishlists,
        'leads': total_leads,
        'orders': orders_count,
        'delivered': status_counts['delivered'],
        'conversion_rate': conversion_rate,
        'intent_rate': intent_conversion_rate,
    }

    # Payment Methods (from distinct orders in this period)
    order_ids = period_items.values_list('order_id', flat=True).distinct()
    period_orders = Order.objects.filter(id__in=order_ids)
    payment_counts = {
        'cod': period_orders.filter(payment_method=Order.PAYMENT_COD).count(),
        'upi': period_orders.filter(payment_method=Order.PAYMENT_UPI).count(),
    }

    # Regional Customer Reach (Phase 3)
    state_aggregates = (
        period_items.exclude(order__state__isnull=True)
        .exclude(order__state='')
        .values('order__state')
        .annotate(
            orders=Count('order_id', distinct=True),
            units=Sum('quantity'),
            revenue=Sum('line_total')
        )
        .order_by('-revenue')[:6]
    )
    regional_reach = []
    for s in state_aggregates:
        pct = round((s['revenue'] / total_revenue * 100), 1) if total_revenue > 0 else 0
        regional_reach.append({
            'state': s['order__state'],
            'orders': s['orders'],
            'units': s['units'],
            'revenue': s['revenue'],
            'percent': pct,
        })

    # Daily aggregation for Chart.js
    daily_aggregates = (
        valid_items.annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(
            daily_revenue=Sum('line_total'),
            daily_units=Sum('quantity'),
            daily_orders=Count('order_id', distinct=True)
        )
        .order_by('date')
    )
    daily_map = {item['date']: item for item in daily_aggregates}

    daily_views_agg = (
        period_views.values('date')
        .annotate(daily_views=Sum('views_count'))
        .order_by('date')
    )
    daily_views_map = {item['date']: item['daily_views'] for item in daily_views_agg}

    chart_labels = []
    chart_revenue = []
    chart_units = []
    chart_views = []

    if num_days:
        for i in range(num_days - 1, -1, -1):
            d = (today - timedelta(days=i))
            chart_labels.append(d.strftime('%d %b'))
            stat = daily_map.get(d)
            chart_revenue.append(float(stat['daily_revenue']) if stat else 0.0)
            chart_units.append(int(stat['daily_units']) if stat else 0)
            chart_views.append(int(daily_views_map.get(d, 0)))
    else:
        for stat in daily_aggregates:
            chart_labels.append(stat['date'].strftime('%d %b %Y'))
            chart_revenue.append(float(stat['daily_revenue']))
            chart_units.append(int(stat['daily_units']))
            chart_views.append(int(daily_views_map.get(stat['date'], 0)))

    # Top selling products in this period with view & conversion metrics
    top_products_qs = (
        valid_items.values('product_id', 'product_name')
        .annotate(
            revenue=Sum('line_total'),
            units_sold=Sum('quantity'),
            order_count=Count('order_id', distinct=True)
        )
        .order_by('-revenue')[:6]
    )
    top_products = []
    for tp in top_products_qs:
        prod = Product.objects.filter(id=tp['product_id']).first() if tp['product_id'] else None
        p_views = period_views.filter(product_id=tp['product_id']).aggregate(t=Sum('views_count'))['t'] or 0
        p_leads = period_leads.filter(product_id=tp['product_id']).count()
        p_conv = round((tp['units_sold'] / p_views * 100), 1) if p_views > 0 else 0.0
        top_products.append({
            'product': prod,
            'name': tp['product_name'],
            'revenue': tp['revenue'],
            'units_sold': tp['units_sold'],
            'order_count': tp['order_count'],
            'views': p_views,
            'leads': p_leads,
            'conversion_rate': p_conv,
        })

    # High Intent / Wishlist Demand
    wishlist_leaders = (
        WishlistItem.objects.filter(product__seller=seller)
        .values('product_id', 'product__name', 'product__price', 'product__stock', 'product__status')
        .annotate(wishlist_count=Count('id'))
        .order_by('-wishlist_count')[:6]
    )

    # Product inventory health
    seller_products = Product.objects.filter(seller=seller)
    total_products_count = seller_products.count()
    out_of_stock_products = seller_products.filter(stock=0)
    low_stock_products = seller_products.filter(stock__gt=0, stock__lte=5)

    # Reviews and Satisfaction
    reviews = Review.objects.filter(product__seller=seller, is_approved=True)
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0
    rating_breakdown = {}
    for star in [5, 4, 3, 2, 1]:
        cnt = reviews.filter(rating=star).count()
        pct = round((cnt / total_reviews * 100), 1) if total_reviews > 0 else 0
        rating_breakdown[star] = {'count': cnt, 'percent': pct}

    # Smart Contextual Insights
    insights = []
    if out_of_stock_products.exists():
        count = out_of_stock_products.count()
        insights.append({
            'type': 'danger',
            'icon': 'bi-exclamation-octagon-fill',
            'title': f'{count} Product{"s are" if count > 1 else " is"} Out of Stock',
            'desc': 'Buyers cannot purchase out-of-stock items. Restock your listings to prevent missed revenue.',
            'action_text': 'Manage Inventory',
            'action_url': reverse('seller:my_products'),
        })
    if total_leads > 0:
        insights.append({
            'type': 'success',
            'icon': 'bi-whatsapp',
            'title': f'{total_leads} Direct WhatsApp Lead{"s" if total_leads > 1 else ""} Received',
            'desc': 'Customers tapped "Ask Maker on WhatsApp" to discuss custom orders and bulk deliveries.',
            'action_text': 'View Inquiries',
            'action_url': '#funnelSection',
        })
    if total_views > 15 and orders_count == 0:
        insights.append({
            'type': 'warning',
            'icon': 'bi-eye-fill',
            'title': f'{total_views} Views with 0 Orders',
            'desc': 'Your crafts are getting discovered! Consider running a 5–10% seller discount to encourage first-time buyers.',
            'action_text': 'Edit Discounts',
            'action_url': reverse('seller:my_products'),
        })
    elif low_stock_products.exists():
        count = low_stock_products.count()
        insights.append({
            'type': 'warning',
            'icon': 'bi-box-seam',
            'title': f'{count} Product{"s have" if count > 1 else " has"} Low Stock (≤ 5 units)',
            'desc': 'Keep popular handmade items available by restocking before units reach zero.',
            'action_text': 'View Low Stock',
            'action_url': reverse('seller:my_products'),
        })
    if status_counts['pending'] > 0:
        insights.append({
            'type': 'primary',
            'icon': 'bi-clock-history',
            'title': f'{status_counts["pending"]} New Order{"s" if status_counts["pending"] > 1 else ""} Awaiting Confirmation',
            'desc': 'Prompt fulfillment builds buyer trust and improves your seller visibility score.',
            'action_text': 'Process Orders',
            'action_url': reverse('seller:orders'),
        })

    context = {
        'seller': seller,
        'range_param': range_param,
        'range_label': range_label,
        'total_revenue': total_revenue,
        'total_units': total_units,
        'orders_count': orders_count,
        'aov': aov,
        'cancelled_count': cancelled_count,
        'cancelled_revenue': cancelled_revenue,
        'total_views': total_views,
        'total_leads': total_leads,
        'total_wishlists': total_wishlists,
        'conversion_rate': conversion_rate,
        'funnel': funnel,
        'status_counts': status_counts,
        'payment_counts': payment_counts,
        'regional_reach': regional_reach,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_revenue_json': json.dumps(chart_revenue),
        'chart_units_json': json.dumps(chart_units),
        'chart_views_json': json.dumps(chart_views),
        'top_products': top_products,
        'wishlist_leaders': wishlist_leaders,
        'total_products_count': total_products_count,
        'out_of_stock_count': out_of_stock_products.count(),
        'low_stock_count': low_stock_products.count(),
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'rating_breakdown': rating_breakdown,
        'insights': insights,
        'active_subscription': seller.get_active_subscription(),
    }
    return render(request, 'seller/analytics.html', context)


@seller_required
def analytics_report(request):
    """Formal print-ready performance & financial statement for artisans."""
    seller = request.user.seller_profile
    range_param = request.GET.get('range', '30d')
    now = timezone.now()
    today = now.date()

    if range_param == '7d':
        start_datetime = now - timedelta(days=7)
        range_label = 'Last 7 Days'
    elif range_param == '90d':
        start_datetime = now - timedelta(days=90)
        range_label = 'Last 90 Days'
    elif range_param == 'year':
        start_datetime = timezone.datetime(now.year, 1, 1, tzinfo=timezone.get_current_timezone())
        range_label = f'Year {now.year}'
    elif range_param == 'all':
        start_datetime = None
        range_label = 'All Time'
    else:
        range_param = '30d'
        start_datetime = now - timedelta(days=30)
        range_label = 'Last 30 Days'

    seller_order_items = OrderItem.objects.filter(seller=seller).select_related('order', 'product')
    if start_datetime:
        period_items = seller_order_items.filter(created_at__gte=start_datetime)
    else:
        period_items = seller_order_items

    valid_items = period_items.exclude(status=OrderItem.STATUS_CANCELLED)
    gross_revenue = valid_items.aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')
    total_units = valid_items.aggregate(qty=Sum('quantity'))['qty'] or 0
    orders_count = period_items.values('order_id').distinct().count()

    cancelled_items = period_items.filter(status=OrderItem.STATUS_CANCELLED)
    cancelled_count = cancelled_items.count()
    cancelled_revenue = cancelled_items.aggregate(total=Sum('line_total'))['total'] or Decimal('0.00')

    delivered_count = period_items.filter(status=OrderItem.STATUS_DELIVERED).count()
    pending_count = period_items.filter(status=OrderItem.STATUS_PENDING).count()
    shipped_count = period_items.filter(status=OrderItem.STATUS_SHIPPED).count()

    # Payment summary
    order_ids = period_items.values_list('order_id', flat=True).distinct()
    period_orders = Order.objects.filter(id__in=order_ids)
    payment_upi = period_orders.filter(payment_method=Order.PAYMENT_UPI).count()
    payment_cod = period_orders.filter(payment_method=Order.PAYMENT_COD).count()

    # Ledger items
    ledger_items = period_items.order_by('-created_at')

    return render(request, 'seller/analytics_report.html', {
        'seller': seller,
        'range_param': range_param,
        'range_label': range_label,
        'generated_at': now,
        'gross_revenue': gross_revenue,
        'total_units': total_units,
        'orders_count': orders_count,
        'delivered_count': delivered_count,
        'pending_count': pending_count,
        'shipped_count': shipped_count,
        'cancelled_count': cancelled_count,
        'cancelled_revenue': cancelled_revenue,
        'net_realizable': gross_revenue,
        'payment_upi': payment_upi,
        'payment_cod': payment_cod,
        'ledger_items': ledger_items,
    })




