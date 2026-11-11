from django.urls import path
from . import views

app_name = 'seller'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/report/', views.analytics_report, name='analytics_report'),
    path('my-products/', views.my_products, name='my_products'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:pk>/', views.edit_product, name='edit_product'),
    path('edit-product/<int:pk>/delete-image/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
    path('edit-product/<int:pk>/delete-cover/', views.delete_cover_image, name='delete_cover_image'),
    path('delete-product/<int:pk>/', views.delete_product, name='delete_product'),
    path('toggle-product-status/<int:pk>/', views.toggle_product_status, name='toggle_product_status'),
    path('promotions/', views.promotions, name='promotions'),
    path('reviews/', views.reviews, name='reviews'),
    path('orders/', views.orders, name='orders'),
    path('orders/<int:item_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('subscription/', views.subscription_plans, name='subscription_plans'),
    path('subscription/checkout/<int:plan_id>/', views.subscribe_checkout, name='subscribe_checkout'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('profile/', views.profile, name='profile'),
]
