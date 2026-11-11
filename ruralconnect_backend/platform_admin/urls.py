from django.urls import path
from . import views

app_name = 'platform_admin'

urlpatterns = [
    path('login/', views.admin_login_view, name='login'),
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    path('pending-products/', views.pending_products, name='pending_products'),
    path('approve-product/<int:pk>/', views.approve_product, name='approve_product'),
    path('reject-product/<int:pk>/', views.reject_product, name='reject_product'),
    path('manage-products/', views.manage_products, name='manage_products'),
    path('change-product-status/<int:pk>/', views.change_product_status, name='change_product_status'),
    path('delete-product/<int:pk>/', views.delete_product, name='delete_product'),
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    path('banners/', views.banners, name='banners'),
    path('campaigns/', views.campaigns, name='campaigns'),
    path('boost-plans/', views.boost_plans, name='boost_plans'),
    path('toggle-seller-suspension/<int:pk>/', views.toggle_seller_suspension, name='toggle_seller_suspension'),
    path('delete-seller/<int:pk>/', views.delete_seller, name='delete_seller'),
    path('review-seller-verification/<int:pk>/', views.review_seller_verification, name='review_seller_verification'),
]
