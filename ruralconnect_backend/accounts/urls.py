from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('register/buyer/', views.register_buyer_view, name='register_buyer'),
    path('register/seller/', views.register_seller_view, name='register_seller'),
    path('verify-email/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('cancel-verification/', views.cancel_verification_view, name='cancel_verification'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('reset-password/resend-otp/', views.resend_reset_otp_view, name='resend_reset_otp'),
    path('reset-password/cancel/', views.cancel_reset_password_view, name='cancel_reset_password'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/addresses/add/', views.address_add_view, name='address_add'),
    path('profile/addresses/<int:address_id>/edit/', views.address_edit_view, name='address_edit'),
    path('profile/addresses/<int:address_id>/set-default/', views.address_set_default_view, name='address_set_default'),
    path('profile/addresses/<int:address_id>/delete/', views.address_delete_view, name='address_delete'),
    path('verification-doc/<int:pk>/', views.view_verification_doc, name='view_verification_doc'),
]

