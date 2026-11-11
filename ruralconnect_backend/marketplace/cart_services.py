"""
Cart service operations: handles cart items for authenticated and anonymous users.
"""

from decimal import Decimal
from django.db.models import Q
from django.urls import reverse
from .models import Product, CartItem


def _get_cart_filter(request):
    """Return filter Q object for current user or session."""
    if request.user.is_authenticated:
        return Q(user=request.user)
    if request.session.session_key:
        return Q(session_key=request.session.session_key, user__isnull=True)
    return None


def get_cart_queryset(request):
    """Return active cart items for current request."""
    q_filter = _get_cart_filter(request)
    if q_filter is None:
        return CartItem.objects.none()
    return CartItem.objects.filter(
        q_filter,
        product__status=Product.STATUS_APPROVED
    ).select_related('product', 'product__seller', 'product__category')


def get_cart_count(request):
    """Return total number of items in the cart."""
    items = get_cart_queryset(request)
    return sum(item.quantity for item in items)


def get_cart_data(request):
    """Return complete cart summary and list of items."""
    cart_items = get_cart_queryset(request)

    items_data = []
    total_count = 0
    total_mrp = Decimal('0')
    subtotal = Decimal('0')

    for item in cart_items:
        p = item.product
        qty = min(item.quantity, p.stock if p.stock > 0 else 1)
        if qty != item.quantity:
            item.quantity = qty
            item.save()

        line_mrp = p.price * qty
        line_total = p.final_price() * qty

        total_count += qty
        total_mrp += line_mrp
        subtotal += line_total

        items_data.append({
            'cart_item_id': item.id,
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'final_price': float(p.final_price()),
            'discount': p.effective_discount(),
            'stock': p.stock,
            'seller': p.seller.business_name if p.seller else 'Rural Artisan',
            'seller_id': p.seller.id if p.seller else None,
            'seller_url': reverse('marketplace:seller_detail', kwargs={'seller_id': p.seller.id}) if p.seller else None,
            'main_image': p.main_image.url if p.main_image else None,
            'emoji': p.emoji,
            'hue': p.hue,
            'url': reverse('marketplace:product_detail', kwargs={'pk': p.pk}),
            'quantity': qty,
            'line_mrp': float(line_mrp),
            'line_total': float(line_total),
        })

    discount_saved = max(Decimal('0'), total_mrp - subtotal)
    delivery = Decimal('0') if (subtotal >= Decimal('999') or total_count == 0) else Decimal('60')
    grand_total = subtotal + delivery if total_count > 0 else Decimal('0')

    return {
        'items': items_data,
        'summary': {
            'total_count': total_count,
            'total_mrp': float(round(total_mrp, 2)),
            'subtotal': float(round(subtotal, 2)),
            'discount_saved': float(round(discount_saved, 2)),
            'delivery': float(delivery),
            'grand_total': float(round(grand_total, 2)),
        }
    }


def add_to_cart(request, product_id, quantity=1):
    """Add a product to cart or increment quantity."""
    try:
        product = Product.objects.get(id=product_id, status=Product.STATUS_APPROVED)
    except Product.DoesNotExist:
        return {'success': False, 'error': 'Product not found or unavailable'}

    if product.stock <= 0:
        return {'success': False, 'error': 'Product is out of stock'}

    quantity = max(1, int(quantity))

    if request.user.is_authenticated:
        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': min(quantity, product.stock)}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock)
            item.save()
    else:
        if not request.session.session_key:
            request.session.save()
        item, created = CartItem.objects.get_or_create(
            session_key=request.session.session_key,
            user__isnull=True,
            product=product,
            defaults={'quantity': min(quantity, product.stock)}
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock)
            item.save()

    return {
        'success': True,
        'message': f'"{product.name}" added to cart',
        'cart_count': get_cart_count(request),
        'item': {
            'id': product.id,
            'name': product.name,
            'quantity': item.quantity,
        }
    }


def update_cart_quantity(request, product_id, delta=None, quantity=None):
    """Update quantity by delta or set absolute quantity."""
    q_filter = _get_cart_filter(request)
    if not q_filter:
        return {'success': False, 'error': 'No active cart session'}

    try:
        item = CartItem.objects.get(q_filter, product_id=product_id)
    except CartItem.DoesNotExist:
        return {'success': False, 'error': 'Item not found in cart'}

    max_stock = item.product.stock if item.product.stock > 0 else 1

    if delta is not None:
        new_qty = item.quantity + int(delta)
    elif quantity is not None:
        new_qty = int(quantity)
    else:
        return {'success': False, 'error': 'No quantity specified'}

    if new_qty <= 0:
        item.delete()
    else:
        item.quantity = min(new_qty, max_stock)
        item.save()

    cart_data = get_cart_data(request)
    return {
        'success': True,
        'cart_count': cart_data['summary']['total_count'],
        'cart': cart_data,
    }


def remove_from_cart(request, product_id):
    """Remove a product completely from the cart."""
    q_filter = _get_cart_filter(request)
    if q_filter:
        CartItem.objects.filter(q_filter, product_id=product_id).delete()

    cart_data = get_cart_data(request)
    return {
        'success': True,
        'message': 'Item removed from cart',
        'cart_count': cart_data['summary']['total_count'],
        'cart': cart_data,
    }


def clear_cart(request):
    """Clear all items from current cart."""
    q_filter = _get_cart_filter(request)
    if q_filter:
        CartItem.objects.filter(q_filter).delete()

    return {
        'success': True,
        'message': 'Cart cleared',
        'cart_count': 0,
        'cart': {
            'items': [],
            'summary': {
                'total_count': 0,
                'total_mrp': 0,
                'subtotal': 0,
                'discount_saved': 0,
                'delivery': 0,
                'grand_total': 0,
            }
        }
    }


def sync_legacy_cart(request, items_list):
    """Sync legacy items from localStorage into user's cart."""
    if not items_list or not isinstance(items_list, list):
        return get_cart_data(request)

    for entry in items_list:
        try:
            pid = int(entry.get('id', 0))
            qty = max(1, int(entry.get('qty', 1)))
            if pid > 0:
                add_to_cart(request, pid, quantity=qty)
        except Exception:
            continue

    return get_cart_data(request)


def merge_guest_cart(request, user, old_session_key=None):
    """Merge guest cart items associated with old_session_key into user's cart."""
    session_key = old_session_key or request.session.session_key
    if not session_key:
        return

    guest_items = CartItem.objects.filter(session_key=session_key, user__isnull=True)
    for guest_item in guest_items:
        existing = CartItem.objects.filter(user=user, product=guest_item.product).first()
        if existing:
            existing.quantity = min(
                existing.quantity + guest_item.quantity,
                guest_item.product.stock if guest_item.product.stock > 0 else 1
            )
            existing.save()
            guest_item.delete()
        else:
            guest_item.user = user
            guest_item.session_key = None
            guest_item.save()
