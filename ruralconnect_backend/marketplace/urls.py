from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='products'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/track-whatsapp/', views.track_whatsapp_click, name='track_whatsapp_click'),
    path('cart/', views.cart, name='cart'),
    path('api/cart-items/', views.cart_items_api, name='cart_items_api'),
    path('cart/api/add/', views.cart_add_api, name='cart_add_api'),
    path('cart/api/update/', views.cart_update_api, name='cart_update_api'),
    path('cart/api/remove/', views.cart_remove_api, name='cart_remove_api'),
    path('cart/api/clear/', views.cart_clear_api, name='cart_clear_api'),
    path('cart/api/sync/', views.cart_sync_api, name='cart_sync_api'),
    path('checkout/api/place-order/', views.checkout_place_order_api, name='checkout_place_order_api'),
    path('orders/success/<str:order_number>/', views.order_success, name='order_success'),
    path('orders/item/<int:item_id>/track/', views.track_order_item_api, name='track_order_item_api'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('sellers/<int:seller_id>/', views.seller_detail, name='seller_detail'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist_view, name='toggle_wishlist'),
    path('wishlist/move-to-cart/<int:product_id>/', views.move_wishlist_to_cart_view, name='move_wishlist_to_cart'),
    path('api/search-suggest/', views.search_suggest_api, name='search_suggest_api'),
]

