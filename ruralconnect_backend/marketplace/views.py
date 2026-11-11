"""Marketplace views: home, product list, product detail, cart, search."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, F
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .models import (
    Category, Product, Banner, Campaign, Review, HeroSlide, SellerCtaBanner,
    Order, OrderItem, WishlistItem, ProductDailyView, WhatsAppLead,
    sync_expired_boosts
)
from .forms import ReviewForm


def home(request):
    import random
    from django.utils import timezone
    today = timezone.now().date()
    sync_expired_boosts()

    categories = Category.objects.all()
    hero_slides = HeroSlide.objects.filter(is_active=True).order_by('order', '-created_at')
    banners = Banner.objects.filter(is_active=True).order_by('order')
    seller_cta = SellerCtaBanner.objects.first()

    # Active Campaigns with randomized products
    from django.db.models import Prefetch
    from .models import CampaignProduct
    active_campaigns = list(Campaign.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today,
    ).prefetch_related(
        Prefetch(
            'campaign_products',
            queryset=CampaignProduct.objects.select_related(
                'product__seller', 'product__category'
            )
        )
    ))

    # Shuffle campaign products so order varies dynamically on every page load
    for camp in active_campaigns:
        camp_prods = [cp for cp in camp.campaign_products.all() if cp.product.status == Product.STATUS_APPROVED]
        random.shuffle(camp_prods)
        camp.shuffled_products = camp_prods

    approved = Product.objects.filter(status=Product.STATUS_APPROVED).select_related(
        'category', 'seller'
    )

    # Featured: top rated (>= 4.0), randomized with sponsored / boosted products prioritized
    featured_candidates = list(
        approved.filter(reviews__is_approved=True)
        .annotate(avg_r=Avg('reviews__rating'))
        .filter(avg_r__gte=4.0)
    )
    feat_sponsored = [p for p in featured_candidates if p.promoted]
    feat_organic = [p for p in featured_candidates if not p.promoted]
    random.shuffle(feat_sponsored)
    random.shuffle(feat_organic)
    featured = (feat_sponsored + feat_organic)[:4]

    # Deals: products with discount >= 15%, randomized with sponsored products prioritized
    all_deals = [p for p in approved if p.effective_discount() >= 15]
    random.shuffle(all_deals)
    deals_sponsored = [p for p in all_deals if p.promoted]
    deals_organic = [p for p in all_deals if not p.promoted]
    deals = (deals_sponsored + deals_organic)[:16]

    # Newly added: Deduplicated from Featured, with max 1 sponsored slot and randomized fresh pool
    featured_ids = [p.id for p in featured]
    available_new = approved.exclude(id__in=featured_ids)

    new_sponsored = list(available_new.filter(promoted=True).order_by('-added')[:4])
    new_organic = list(available_new.filter(promoted=False).order_by('-added')[:12])

    random.shuffle(new_sponsored)
    random.shuffle(new_organic)

    # Reserve at most 1 slot for sponsored to ensure organic new arrivals get prime exposure
    lead_sponsored = new_sponsored[:1] if new_sponsored else []
    slots_left = 4 - len(lead_sponsored)
    chosen_organic = new_organic[:slots_left]
    new_products = lead_sponsored + chosen_organic
    if len(new_products) < 4 and len(new_sponsored) > 1:
        new_products += new_sponsored[1: 4 - len(new_products) + 1]

    # Sponsored Spotlight: randomized on every page reload so every artisan gets rotation
    sponsored = list(approved.filter(promoted=True).order_by('?')[:16])

    # Local: sponsored products showing FIRST
    local = approved.filter(location__icontains='Kerala').order_by('-promoted', '-added')[:4]
    trends = list(approved.order_by('-promoted', '-added')[:4])

    context = {
        'categories': categories,
        'hero_slides': hero_slides,
        'banners': banners,
        'active_campaigns': active_campaigns,
        'featured': featured,
        'deals': deals,
        'new_products': new_products,
        'sponsored': sponsored,
        'local': local,
        'trends': trends,
        'seller_cta': seller_cta,
    }
    return render(request, 'marketplace/home.html', context)



def product_list(request):
    sync_expired_boosts()
    categories = Category.objects.all()
    products = Product.objects.filter(status=Product.STATUS_APPROVED).select_related(
        'category', 'seller'
    )

    # --- Filtering ---
    cat_slug = request.GET.get('cat', '')
    campaign_id = request.GET.get('campaign', '')
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    loc = request.GET.get('loc', '')

    active_category = None
    if cat_slug:
        active_category = get_object_or_404(Category, slug=cat_slug)
        products = products.filter(category=active_category)

    active_campaign = None
    if campaign_id:
        try:
            active_campaign = Campaign.objects.get(pk=campaign_id)
            products = products.filter(campaign_products__campaign=active_campaign)
        except (Campaign.DoesNotExist, ValueError):
            pass

    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q) |
            Q(seller__business_name__icontains=q)
        )

    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass

    if loc:
        products = products.filter(location__icontains=loc)

    # --- Sorting: Sponsored / Boosted products show FIRST ---
    if sort == 'price_asc':
        products = products.order_by('-promoted', 'price')
    elif sort == 'price_desc':
        products = products.order_by('-promoted', '-price')
    elif sort == 'newest':
        products = products.order_by('-promoted', '-added')
    elif sort == 'rating':
        products = products.annotate(avg_r=Avg('reviews__rating')).order_by('-promoted', '-avg_r')
    else:
        # Default: sponsored items first, then newly added
        products = products.order_by('-promoted', '-added')

    return render(request, 'marketplace/products.html', {
        'products': products,
        'categories': categories,
        'active_category': active_category,
        'active_campaign': active_campaign,
        'q': q,
        'sort': sort,
        'cat_slug': cat_slug,
        'campaign_id': campaign_id,
    })


def product_detail(request, pk):
    base_qs = Product.objects.select_related('category', 'seller').prefetch_related('images', 'reviews__reviewer')
    if request.user.is_authenticated and (
        request.user.is_staff or 
        (hasattr(request.user, 'seller_profile') and base_qs.filter(pk=pk, seller=request.user.seller_profile).exists())
    ):
        product = get_object_or_404(base_qs, pk=pk)
    else:
        product = get_object_or_404(base_qs, pk=pk, status=Product.STATUS_APPROVED)

    reviews = product.reviews.filter(is_approved=True)
    related = Product.objects.filter(
        category=product.category, status=Product.STATUS_APPROVED
    ).exclude(pk=pk).order_by('-promoted', '-added')[:4]

    # Check review permissions
    user_reviewed = False
    is_own_product = False
    review_form = None

    if request.user.is_authenticated:
        is_own_product = hasattr(request.user, 'seller_profile') and product.seller == request.user.seller_profile
        user_reviewed = product.reviews.filter(reviewer=request.user).exists()

        if not is_own_product and not user_reviewed:
            if request.method == 'POST' and 'submit_review' in request.POST:
                review_form = ReviewForm(request.POST)
                if review_form.is_valid():
                    rev = review_form.save(commit=False)
                    rev.product = product
                    rev.reviewer = request.user
                    rev.is_approved = True
                    rev.save()
                    messages.success(request, 'Thank you! Your review has been submitted.')
                    return redirect('marketplace:product_detail', pk=pk)
            else:
                review_form = ReviewForm()

    # Track views (exclude seller viewing own craft; deduplicate rapid session refreshes)
    if not is_own_product and product.is_public() and hasattr(request, 'session'):
        viewed_products = request.session.setdefault('viewed_products', [])
        if product.id not in viewed_products:
            today = timezone.now().date()
            pv, created = ProductDailyView.objects.get_or_create(
                product=product,
                date=today,
                defaults={'seller': product.seller, 'views_count': 1}
            )
            if not created:
                ProductDailyView.objects.filter(pk=pv.pk).update(views_count=F('views_count') + 1)
            viewed_products.append(product.id)
            if len(viewed_products) > 100:
                viewed_products.pop(0)
            if hasattr(request.session, 'modified'):
                request.session.modified = True


    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'related': related,
        'user_reviewed': user_reviewed,
        'is_own_product': is_own_product,
        'review_form': review_form,
        'final_price': product.final_price(),
        'discount': product.effective_discount(),
    })


def track_whatsapp_click(request, pk):
    """Track clicks on WhatsApp inquiry button for artisan leads."""
    product = get_object_or_404(Product, pk=pk)
    is_own = request.user.is_authenticated and hasattr(request.user, 'seller_profile') and product.seller == request.user.seller_profile
    if not is_own:
        WhatsAppLead.objects.create(
            product=product,
            seller=product.seller,
            user=request.user if request.user.is_authenticated else None,
        )
    return JsonResponse({
        'status': 'ok',
        'whatsapp_url': product.get_whatsapp_inquiry_url(request)
    })



import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from . import cart_services


def cart(request):
    """Cart page – renders cart items and saved delivery addresses for the user."""
    cart_data = cart_services.get_cart_data(request)
    delivery_addresses = []
    default_address = None
    if request.user.is_authenticated:
        delivery_addresses = list(request.user.delivery_addresses.all())
        default_address = next((a for a in delivery_addresses if a.is_default), delivery_addresses[0] if delivery_addresses else None)

    return render(request, 'marketplace/cart.html', {
        'cart_data': cart_data,
        'delivery_addresses': delivery_addresses,
        'default_address': default_address,
    })


def cart_items_api(request):
    """Return JSON details for current user's cart (or legacy ?ids= param if specified)."""
    ids_str = request.GET.get('ids', '')
    if ids_str:
        try:
            id_list = [int(i.strip()) for i in ids_str.split(',') if i.strip().isdigit()]
        except Exception:
            id_list = []

        products = Product.objects.filter(id__in=id_list, status=Product.STATUS_APPROVED).select_related(
            'seller', 'category'
        )
        items = []
        for p in products:
            items.append({
                'id': p.id,
                'name': p.name,
                'price': float(p.price),
                'final_price': float(p.final_price()),
                'discount': p.effective_discount(),
                'stock': p.stock,
                'seller': p.seller.business_name if p.seller else 'Rural Artisan',
                'main_image': p.main_image.url if p.main_image else None,
                'emoji': p.emoji,
                'hue': p.hue,
                'url': reverse('marketplace:product_detail', kwargs={'pk': p.pk}),
            })
        return JsonResponse({'items': items})

    # Authoritative cart for current user / session
    cart_data = cart_services.get_cart_data(request)
    return JsonResponse({
        'success': True,
        'items': cart_data['items'],
        'summary': cart_data['summary'],
        'cart_count': cart_data['summary']['total_count'],
    })


def _get_post_data(request):
    """Extract dict from JSON body or POST form data."""
    if request.body:
        try:
            return json.loads(request.body.decode('utf-8'))
        except Exception:
            pass
    return request.POST


@require_POST
def cart_add_api(request):
    """API endpoint to add a product to the cart."""
    data = _get_post_data(request)
    product_id = data.get('product_id') or data.get('id')
    quantity = data.get('quantity') or data.get('qty', 1)

    if not product_id:
        return JsonResponse({'success': False, 'error': 'Missing product_id'}, status=400)

    try:
        product_id = int(product_id)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid parameters'}, status=400)

    res = cart_services.add_to_cart(request, product_id, quantity)
    return JsonResponse(res, status=200 if res.get('success') else 400)


@require_POST
def cart_update_api(request):
    """API endpoint to update product quantity (absolute or delta)."""
    data = _get_post_data(request)
    product_id = data.get('product_id') or data.get('id')
    delta = data.get('delta')
    quantity = data.get('quantity') or data.get('qty')

    if not product_id:
        return JsonResponse({'success': False, 'error': 'Missing product_id'}, status=400)

    try:
        product_id = int(product_id)
        delta = int(delta) if delta is not None else None
        quantity = int(quantity) if quantity is not None else None
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid parameters'}, status=400)

    res = cart_services.update_cart_quantity(request, product_id, delta=delta, quantity=quantity)
    return JsonResponse(res, status=200 if res.get('success') else 400)


@require_POST
def cart_remove_api(request):
    """API endpoint to remove a product from the cart."""
    data = _get_post_data(request)
    product_id = data.get('product_id') or data.get('id')

    if not product_id:
        return JsonResponse({'success': False, 'error': 'Missing product_id'}, status=400)

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid product_id'}, status=400)

    res = cart_services.remove_from_cart(request, product_id)
    return JsonResponse(res)


@require_POST
def cart_clear_api(request):
    """API endpoint to clear all items in the cart."""
    res = cart_services.clear_cart(request)
    return JsonResponse(res)


@require_POST
def cart_sync_api(request):
    """API endpoint to sync legacy localStorage cart items to user's database cart."""
    data = _get_post_data(request)
    legacy_items = data.get('legacy_items', [])
    res = cart_services.sync_legacy_cart(request, legacy_items)
    return JsonResponse({
        'success': True,
        'cart': res,
        'cart_count': res['summary']['total_count'],
    })


@require_POST
def checkout_place_order_api(request):
    """
    API endpoint to convert cart items into a confirmed Order + OrderItems.
    Decrements stock, clears the cart, and returns order redirect.
    """
    if not request.user.is_authenticated:
        login_url = f"{reverse('accounts:login')}?next={reverse('marketplace:cart')}"
        return JsonResponse({
            'success': False,
            'login_required': True,
            'login_url': login_url,
            'error': 'Please sign in or create an account to complete your order.'
        }, status=401)

    data = _get_post_data(request)
    full_name = (data.get('full_name') or request.user.full_name or '').strip()
    phone = (data.get('phone') or getattr(request.user, 'phone', '') or '').strip()
    shipping_address = (data.get('shipping_address') or '').strip()
    city = (data.get('city') or '').strip()
    state = (data.get('state') or 'Kerala').strip()
    postal_code = (data.get('postal_code') or '').strip()
    raw_payment_method = data.get('payment_method', 'cod')
    payment_method = raw_payment_method if raw_payment_method in [Order.PAYMENT_COD, Order.PAYMENT_UPI] else Order.PAYMENT_COD
    order_notes = (data.get('order_notes') or '').strip()

    if not full_name:
        return JsonResponse({'success': False, 'error': 'Recipient name is required.'}, status=400)
    if not phone:
        return JsonResponse({'success': False, 'error': 'Contact phone number is required.'}, status=400)
    if not shipping_address or not city or not postal_code:
        return JsonResponse({'success': False, 'error': 'Complete delivery address (address, city, postal code) is required.'}, status=400)

    cart_data = cart_services.get_cart_data(request)
    items = cart_data.get('items', [])
    if not items:
        return JsonResponse({'success': False, 'error': 'Your cart is empty.'}, status=400)

    from decimal import Decimal
    import uuid

    try:
        with transaction.atomic():
            product_map = {}
            for item in items:
                p = Product.objects.select_for_update().get(id=item['id'])
                if p.stock < item['quantity']:
                    return JsonResponse({
                        'success': False,
                        'error': f"Only {p.stock} units available for '{p.name}'. Please update quantity."
                    }, status=400)
                product_map[item['id']] = p

            date_str = timezone.now().strftime('%y%m%d')
            while True:
                rand_hex = uuid.uuid4().hex[:6].upper()
                order_number = f"RC{date_str}{rand_hex}"
                if not Order.objects.filter(order_number=order_number).exists():
                    break

            order = Order.objects.create(
                order_number=order_number,
                buyer=request.user,
                full_name=full_name,
                phone=phone,
                shipping_address=shipping_address,
                city=city,
                state=state,
                postal_code=postal_code,
                subtotal=Decimal(str(cart_data['summary']['subtotal'])),
                delivery_fee=Decimal(str(cart_data['summary']['delivery'])),
                discount_saved=Decimal(str(cart_data['summary']['discount_saved'])),
                total_amount=Decimal(str(cart_data['summary']['grand_total'])),
                payment_method=payment_method,
                payment_status='pending',
                status=Order.STATUS_PENDING,
                order_notes=order_notes,
            )

            for item in items:
                p = product_map[item['id']]
                qty = item['quantity']
                OrderItem.objects.create(
                    order=order,
                    product=p,
                    seller=p.seller,
                    product_name=p.name,
                    unit_price=Decimal(str(item['final_price'])),
                    quantity=qty,
                    line_total=Decimal(str(item['line_total'])),
                    status=OrderItem.STATUS_PENDING,
                )
                p.stock = max(0, p.stock - qty)
                p.save(update_fields=['stock'])

            cart_services.clear_cart(request)

            save_to_profile = data.get('save_to_profile', True)
            if save_to_profile:
                try:
                    from accounts.models import DeliveryAddress, BuyerProfile
                    matching = DeliveryAddress.objects.filter(
                        user=request.user,
                        street_address=shipping_address,
                        postal_code=postal_code,
                    ).first()
                    if not matching:
                        is_first = not DeliveryAddress.objects.filter(user=request.user).exists()
                        DeliveryAddress.objects.create(
                            user=request.user,
                            full_name=full_name,
                            phone=phone,
                            address_type=DeliveryAddress.TYPE_HOME,
                            street_address=shipping_address,
                            city=city,
                            state=state,
                            postal_code=postal_code,
                            is_default=is_first,
                        )
                    # Sync to BuyerProfile
                    bp, _ = BuyerProfile.objects.get_or_create(user=request.user)
                    bp.shipping_address = shipping_address
                    bp.city = city
                    bp.state = state
                    bp.postal_code = postal_code
                    bp.save()
                    if phone and not request.user.phone:
                        request.user.phone = phone
                        request.user.save(update_fields=['phone'])
                except Exception:
                    pass

        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'redirect_url': reverse('marketplace:order_success', kwargs={'order_number': order.order_number}),
            'message': 'Order placed successfully!'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to process order: {str(e)}'}, status=500)


@login_required
def order_success(request, order_number):
    """Thank you / Order confirmation screen for the buyer."""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__seller'),
        order_number=order_number
    )
    if not request.user.is_staff and order.buyer != request.user:
        messages.error(request, 'Access denied.')
        return redirect('marketplace:home')

    return render(request, 'marketplace/order_success.html', {
        'order': order,
    })


def my_orders(request):
    """List of orders placed by the current authenticated buyer."""
    if not request.user.is_authenticated:
        messages.info(request, 'Please sign in to view your orders.')
        return redirect(f"{reverse('accounts:login')}?next={reverse('marketplace:my_orders')}")

    orders = Order.objects.filter(buyer=request.user).prefetch_related('items__product', 'items__seller').order_by('-created_at')
    return render(request, 'marketplace/my_orders.html', {
        'orders': orders,
    })


def seller_detail(request, seller_id):
    """
    Public storefront for an artisan/seller.
    Displays verified identity, regional provenance, heritage story/bio,
    buyer reviews, trust guarantees, and their active product catalog.
    (Private contact/financial details are strictly omitted).
    """
    from accounts.models import SellerProfile
    seller = get_object_or_404(
        SellerProfile.objects.select_related('user'),
        pk=seller_id
    )

    # Active products sold by this seller
    all_seller_products = Product.objects.filter(
        seller=seller,
        status=Product.STATUS_APPROVED
    ).select_related('category', 'seller')

    # Categories represented in this seller's products
    seller_category_ids = all_seller_products.values_list('category_id', flat=True).distinct()
    seller_categories = Category.objects.filter(id__in=seller_category_ids)

    # Filter by category if requested
    cat_slug = request.GET.get('cat', '').strip()
    active_category = None
    products = all_seller_products
    if cat_slug:
        active_category = get_object_or_404(Category, slug=cat_slug)
        products = products.filter(category=active_category)

    # Search keyword within seller's store
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    # Sorting
    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'discount':
        products = products.order_by('-seller_discount', '-added')
    elif sort == 'rating':
        products = products.annotate(avg_r=Avg('reviews__rating')).order_by('-avg_r', '-added')
    else:  # newest
        products = products.order_by('-added')

    # Reviews received across all products of this seller
    reviews = Review.objects.filter(
        product__seller=seller,
        is_approved=True
    ).select_related('reviewer', 'product').order_by('-created_at')

    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
    avg_rating_rounded = round(avg_rating, 1)

    # Total active products count
    total_active_products = all_seller_products.count()

    return render(request, 'marketplace/seller_detail.html', {
        'seller': seller,
        'products': products,
        'total_active_products': total_active_products,
        'seller_categories': seller_categories,
        'active_category': active_category,
        'reviews': reviews[:12],
        'total_reviews': total_reviews,
        'avg_rating': avg_rating_rounded,
        'current_sort': sort,
        'search_query': q,
    })


@login_required(login_url='accounts:login')
def wishlist_view(request):
    """Display buyer's saved wishlist items."""
    wishlist_items = (
        request.user.wishlist_items
        .select_related('product__seller', 'product__category')
        .prefetch_related('product__reviews')
        .order_by('-created_at')
    )
    total_items = wishlist_items.count()
    return render(request, 'marketplace/wishlist.html', {
        'wishlist_items': wishlist_items,
        'total_items': total_items,
    })


def toggle_wishlist_view(request, product_id):
    """AJAX endpoint to add or remove a product from the buyer's wishlist."""
    if not request.user.is_authenticated:
        referer = request.META.get('HTTP_REFERER') or reverse('marketplace:products')
        login_url = f"{reverse('accounts:login')}?next={referer}"
        return JsonResponse({
            'success': False,
            'authenticated': False,
            'login_url': login_url,
            'message': 'Please sign in to save items to your wishlist.',
        }, status=401)

    product = get_object_or_404(Product, id=product_id, status=Product.STATUS_APPROVED)
    wishlist_item = WishlistItem.objects.filter(user=request.user, product=product).first()

    if wishlist_item:
        wishlist_item.delete()
        added = False
        message = f'Removed "{product.name}" from your wishlist'
    else:
        WishlistItem.objects.create(user=request.user, product=product)
        added = True
        message = f'Saved "{product.name}" to your wishlist'

    wishlist_count = request.user.wishlist_items.count()
    return JsonResponse({
        'success': True,
        'authenticated': True,
        'added': added,
        'message': message,
        'wishlist_count': wishlist_count,
        'product_id': product.id,
    })


def move_wishlist_to_cart_view(request, product_id):
    """Move an item from wishlist to cart."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'authenticated': False,
            'login_url': reverse('accounts:login'),
            'message': 'Please sign in to proceed.',
        }, status=401)

    product = get_object_or_404(Product, id=product_id, status=Product.STATUS_APPROVED)
    if product.stock <= 0:
        return JsonResponse({
            'success': False,
            'error': f'"{product.name}" is currently out of stock.',
        }, status=400)

    from . import cart_services
    res = cart_services.add_to_cart(request, product_id, quantity=1)
    if res.get('success'):
        WishlistItem.objects.filter(user=request.user, product=product).delete()
        wishlist_count = request.user.wishlist_items.count()
        return JsonResponse({
            'success': True,
            'message': f'Moved "{product.name}" to cart',
            'cart_count': res.get('cart_count', 0),
            'wishlist_count': wishlist_count,
            'product_id': product.id,
        })
    else:
        return JsonResponse({
            'success': False,
            'error': res.get('error', 'Could not add item to cart'),
        }, status=400)


def search_suggest_api(request):
    """
    Fast JSON endpoint for live search autocomplete.
    Returns top matching products, categories, and verified artisans.
    """
    q = request.GET.get('q', '').strip()
    cat_slug = request.GET.get('cat', '').strip()

    if len(q) < 2:
        return JsonResponse({
            'query': q,
            'products': [],
            'categories': [],
            'artisans': [],
            'total_matches': 0,
        })

    from accounts.models import SellerProfile

    # 1. Product matching (title, description, seller business name)
    product_qs = Product.objects.filter(status=Product.STATUS_APPROVED).select_related('seller', 'category')
    if cat_slug:
        product_qs = product_qs.filter(category__slug=cat_slug)

    product_matches = product_qs.filter(
        Q(name__icontains=q) |
        Q(description__icontains=q) |
        Q(seller__business_name__icontains=q)
    )

    total_product_matches = product_matches.count()
    top_products = list(product_matches[:4])

    products_data = []
    for p in top_products:
        final_price = p.final_price()
        image_url = p.main_image.url if p.main_image else None
        products_data.append({
            'id': p.id,
            'name': p.name,
            'url': reverse('marketplace:product_detail', args=[p.id]),
            'price': float(final_price),
            'original_price': float(p.price),
            'has_discount': final_price < p.price,
            'image_url': image_url,
            'emoji': p.emoji or '📦',
            'category_name': p.category.name if p.category else '',
            'seller_name': p.seller.business_name if p.seller else '',
        })

    # 2. Category matching (only if not already scoped to a category)
    categories_data = []
    if not cat_slug:
        category_matches = Category.objects.filter(name__icontains=q)[:3]
        for c in category_matches:
            categories_data.append({
                'name': c.name,
                'slug': c.slug,
                'emoji': c.emoji,
                'url': f"{reverse('marketplace:products')}?cat={c.slug}",
            })

    # 3. Artisan / Seller matching (artisans with live approved products)
    artisan_matches = SellerProfile.objects.filter(
        products__status=Product.STATUS_APPROVED
    ).filter(
        Q(business_name__icontains=q) | Q(location__icontains=q)
    ).distinct()[:2]

    artisans_data = []
    for a in artisan_matches:
        artisans_data.append({
            'id': a.id,
            'business_name': a.business_name,
            'location': a.location,
            'url': reverse('marketplace:seller_detail', args=[a.id]),
            'avatar_letter': (a.business_name[:1].upper() if a.business_name else 'A'),
        })

    return JsonResponse({
        'query': q,
        'products': products_data,
        'categories': categories_data,
        'artisans': artisans_data,
        'total_matches': total_product_matches,
    })


def track_order_item_api(request, item_id):
    """
    Returns live courier tracking info and scan timeline for an OrderItem.
    Accessible by the buyer who placed the order, the seller, or admin.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required.'}, status=401)

    item = get_object_or_404(
        OrderItem.objects.select_related('order', 'seller', 'product'),
        id=item_id
    )

    is_buyer = (item.order.buyer == request.user)
    is_seller = (hasattr(request.user, 'seller_profile') and item.seller == request.user.seller_profile)
    is_admin = (request.user.is_staff or getattr(request.user, 'role', '') == 'admin')

    if not (is_buyer or is_seller or is_admin):
        return JsonResponse({'success': False, 'error': 'You do not have permission to track this item.'}, status=403)

    from .tracking_services import track_shipment
    tracking_data = track_shipment(item)
    return JsonResponse(tracking_data)




