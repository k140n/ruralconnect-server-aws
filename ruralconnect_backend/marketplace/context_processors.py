from .models import Category
from .cart_services import get_cart_count


def global_context(request):
    """Inject categories, cart count, and wishlist state into every template."""
    categories = Category.objects.all()
    wishlist_product_ids = set()
    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_product_ids = set(request.user.wishlist_items.values_list('product_id', flat=True))
        wishlist_count = len(wishlist_product_ids)

    return {
        'categories': categories,
        'cart_count': get_cart_count(request),
        'wishlist_count': wishlist_count,
        'wishlist_product_ids': wishlist_product_ids,
    }
