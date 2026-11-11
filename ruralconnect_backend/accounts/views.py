"""Account views: login, logout, register."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, FileResponse
import mimetypes
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .forms import SellerRegistrationForm, EmailLoginForm, BuyerProfileForm, PersonalDetailsForm, DeliveryAddressForm
from .models import User, BuyerProfile, SellerProfile, DeliveryAddress
from marketplace.cart_services import merge_guest_cart
from ruralconnect_backend.security_utils import get_safe_redirect_url


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    # Determine which tab to show (buyer or seller)
    role_tab = request.GET.get('role') or request.GET.get('tab') or 'buyer'
    if role_tab not in ['buyer', 'seller']:
        role_tab = 'buyer'

    buyer_form = EmailLoginForm()
    seller_form = EmailLoginForm(prefix='seller')
    error = None

    if request.method == 'POST':
        login_type = request.POST.get('login_type', 'buyer')
        if login_type == 'seller':
            form = EmailLoginForm(request, data=request.POST, prefix='seller')
            role_tab = 'seller'
            if form.is_valid():
                user = form.get_user()
                if user.role != User.ROLE_SELLER:
                    if user.role == User.ROLE_BUYER:
                        error = 'This account is registered as a Buyer. Please switch to the Buyer Login tab.'
                    elif user.role == User.ROLE_ADMIN:
                        error = 'Platform administrator accounts cannot sign in through the seller portal.'
                    else:
                        error = 'Access restricted to Seller accounts only.'
                    seller_form = form
                else:
                    if request.POST.get('remember'):
                        request.session.set_expiry(1209600)
                    old_session_key = request.session.session_key
                    login(request, user)
                    merge_guest_cart(request, user, old_session_key)
                    next_url = request.GET.get('next') or request.POST.get('next')
                    return redirect(get_safe_redirect_url(request, next_url, reverse('seller:dashboard')))
            else:
                email_input = request.POST.get('seller-username', '').strip().lower()
                pw_input = request.POST.get('seller-password', '')
                if email_input and pw_input:
                    unverified = User.objects.filter(email=email_input, is_active=False).first()
                    if unverified and unverified.check_password(pw_input):
                        request.session['verification_email'] = unverified.email
                        generate_and_send_otp(unverified.email, user_name=unverified.full_name)
                        messages.info(request, "Your email is not verified yet. We have sent a 6-digit verification code to complete your signup.")
                        return redirect('accounts:verify_otp')
                seller_form = form
        else:
            form = EmailLoginForm(request, data=request.POST)
            role_tab = 'buyer'
            if form.is_valid():
                user = form.get_user()
                if user.role != User.ROLE_BUYER:
                    if user.role == User.ROLE_SELLER:
                        error = 'This account is registered as a Seller. Please switch to the Seller Login tab.'
                    elif user.role == User.ROLE_ADMIN:
                        error = 'Platform administrator accounts cannot sign in through the buyer portal.'
                    else:
                        error = 'Access restricted to Buyer accounts only.'
                    buyer_form = form
                else:
                    if request.POST.get('remember'):
                        request.session.set_expiry(1209600)
                    old_session_key = request.session.session_key
                    login(request, user)
                    merge_guest_cart(request, user, old_session_key)
                    next_url = request.GET.get('next') or request.POST.get('next')
                    return redirect(get_safe_redirect_url(request, next_url, reverse('marketplace:home')))
            else:
                email_input = request.POST.get('username', '').strip().lower()
                pw_input = request.POST.get('password', '')
                if email_input and pw_input:
                    unverified = User.objects.filter(email=email_input, is_active=False).first()
                    if unverified and unverified.check_password(pw_input):
                        request.session['verification_email'] = unverified.email
                        generate_and_send_otp(unverified.email, user_name=unverified.full_name)
                        messages.info(request, "Your email is not verified yet. We have sent a 6-digit verification code to complete your signup.")
                        return redirect('accounts:verify_otp')
                buyer_form = form

    return render(request, 'accounts/login.html', {

        'buyer_form': buyer_form,
        'seller_form': seller_form,
        'active_tab': role_tab,
        'error': error,
    })


def logout_view(request):
    logout(request)
    return redirect('marketplace:home')


from django.urls import reverse
from .forms import SellerRegistrationForm, BuyerRegistrationForm, EmailLoginForm
from .otp_services import (
    generate_and_send_otp,
    generate_and_send_reset_otp,
    verify_email_otp,
    get_resend_cooldown_seconds,
)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    role_tab = request.GET.get('role', 'buyer').lower()
    if role_tab not in ['buyer', 'seller']:
        role_tab = 'buyer'

    buyer_form = BuyerRegistrationForm()
    seller_form = SellerRegistrationForm()

    if request.method == 'POST':
        reg_type = request.POST.get('reg_type', 'buyer')
        if reg_type == 'seller':
            seller_form = SellerRegistrationForm(request.POST)
            if seller_form.is_valid():
                email = seller_form.cleaned_data['email']
                # Clean up any unverified account using this email
                User.objects.filter(email=email, is_active=False).delete()

                user = seller_form.save(commit=False)
                user.is_active = False
                user.save()

                SellerProfile.objects.create(
                    user=user,
                    business_name=seller_form.cleaned_data['business_name'],
                    location=seller_form.cleaned_data['location'],
                )

                request.session['verification_email'] = user.email
                generate_and_send_otp(user.email, user_name=user.full_name)
                return redirect('accounts:verify_otp')
            role_tab = 'seller'
        else:
            buyer_form = BuyerRegistrationForm(request.POST)
            if buyer_form.is_valid():
                email = buyer_form.cleaned_data['email']
                # Clean up any unverified account using this email
                User.objects.filter(email=email, is_active=False).delete()

                user = buyer_form.save(commit=False)
                user.is_active = False
                user.save()

                request.session['verification_email'] = user.email
                generate_and_send_otp(user.email, user_name=user.full_name)
                return redirect('accounts:verify_otp')
            role_tab = 'buyer'

    return render(request, 'accounts/register.html', {
        'buyer_form': buyer_form,
        'seller_form': seller_form,
        'active_tab': role_tab,
    })


def verify_otp_view(request):
    """Screen for user to enter the 6-digit code sent to their email."""
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    email = request.session.get('verification_email')
    if not email:
        messages.info(request, "No pending email verification found. Please register or sign in.")
        return redirect('accounts:register')

    user = User.objects.filter(email=email, is_active=False).first()
    if not user:
        if User.objects.filter(email=email, is_active=True).exists():
            messages.success(request, "Your account is already verified! Please sign in.")
            return redirect('accounts:login')
        messages.error(request, "Verification session expired. Please register again.")
        return redirect('accounts:register')

    error = None
    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()
        success, msg = verify_email_otp(email, otp_code)
        if success:
            user.is_active = True
            user.save(update_fields=['is_active'])

            if user.role == User.ROLE_BUYER:
                BuyerProfile.objects.get_or_create(user=user)

            old_session_key = request.session.session_key
            login(request, user)
            merge_guest_cart(request, user, old_session_key)

            request.session.pop('verification_email', None)
            messages.success(request, f"Welcome to RuralConnect, {user.full_name}! Your email has been verified.")

            if user.is_seller:
                return redirect('seller:dashboard')
            return redirect('marketplace:home')
        else:
            error = msg

    cooldown_seconds = get_resend_cooldown_seconds(email)

    return render(request, 'accounts/verify_otp.html', {
        'email': email,
        'user_name': user.full_name,
        'error': error,
        'cooldown_seconds': cooldown_seconds,
    })


def resend_otp_view(request):
    """Resend a new 6-digit verification code, respecting 60s cooldown."""
    if request.method != 'POST':
        return redirect('accounts:verify_otp')

    email = request.session.get('verification_email')
    if not email:
        messages.error(request, "No pending email verification found.")
        return redirect('accounts:register')

    user = User.objects.filter(email=email, is_active=False).first()
    if not user:
        messages.error(request, "Registration session expired. Please register again.")
        return redirect('accounts:register')

    success, msg, _ = generate_and_send_otp(email, user_name=user.full_name)
    if success:
        messages.success(request, "A fresh verification code has been sent to your email.")
    else:
        messages.warning(request, msg)

    return redirect('accounts:verify_otp')


def cancel_verification_view(request):
    """Allow user to discard unverified signup and change email."""
    email = request.session.get('verification_email')
    if email:
        User.objects.filter(email=email, is_active=False).delete()
        request.session.pop('verification_email', None)
    return redirect('accounts:register')


def forgot_password_view(request):
    """Allow user to request an OTP code to reset password."""
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    error = None
    email_value = ''

    if request.method == 'POST':
        email_value = request.POST.get('email', '').strip().lower()
        if not email_value:
            error = "Please enter your registered email address."
        else:
            user = User.objects.filter(email=email_value, is_active=True).first()
            if not user:
                inactive_user = User.objects.filter(email=email_value, is_active=False).first()
                if inactive_user:
                    error = "Your account is not verified yet. Please sign in to complete verification."
                else:
                    error = "No active account found with this email address."
            else:
                success, msg, _ = generate_and_send_reset_otp(user.email, user_name=user.full_name)
                if not success:
                    error = msg
                else:
                    request.session['reset_password_email'] = user.email
                    messages.info(request, f"We have sent a 6-digit password reset code to {user.email}.")
                    return redirect('accounts:reset_password')

    return render(request, 'accounts/forgot_password.html', {
        'error': error,
        'email': email_value,
    })


def reset_password_view(request):
    """Verify OTP and set a new password."""
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    email = request.session.get('reset_password_email')
    if not email:
        messages.info(request, "Please enter your email to request a password reset.")
        return redirect('accounts:forgot_password')

    user = User.objects.filter(email=email, is_active=True).first()
    if not user:
        request.session.pop('reset_password_email', None)
        messages.error(request, "Account not found or inactive. Please try again.")
        return redirect('accounts:forgot_password')

    error = None
    if request.method == 'POST':
        otp_code = request.POST.get('otp', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
            error = "Please enter the valid 6-digit verification code sent to your email."
        elif not new_password or len(new_password) < 8:
            error = "Your new password must be at least 8 characters long."
        elif new_password != confirm_password:
            error = "Passwords do not match. Please re-enter."
        else:
            success, msg = verify_email_otp(email, otp_code)
            if not success:
                error = msg
            else:
                user.set_password(new_password)
                user.save(update_fields=['password'])
                request.session.pop('reset_password_email', None)
                messages.success(request, "Your password has been reset successfully! Please log in with your new password.")
                if user.is_seller:
                    return redirect(f"{reverse('accounts:login')}?role=seller")
                return redirect('accounts:login')

    cooldown_seconds = get_resend_cooldown_seconds(email)

    return render(request, 'accounts/reset_password.html', {
        'email': email,
        'user_name': user.full_name,
        'error': error,
        'cooldown_seconds': cooldown_seconds,
    })


def resend_reset_otp_view(request):
    """Resend a new 6-digit password reset code, respecting 60s cooldown."""
    if request.method != 'POST':
        return redirect('accounts:reset_password')

    email = request.session.get('reset_password_email')
    if not email:
        messages.error(request, "No pending password reset session found.")
        return redirect('accounts:forgot_password')

    user = User.objects.filter(email=email, is_active=True).first()
    if not user:
        messages.error(request, "Account not found or inactive.")
        return redirect('accounts:forgot_password')

    success, msg, _ = generate_and_send_reset_otp(email, user_name=user.full_name)
    if success:
        messages.success(request, "A fresh password reset code has been sent to your email.")
    else:
        messages.warning(request, msg)

    return redirect('accounts:reset_password')


def cancel_reset_password_view(request):
    """Clear reset session and return to forgot password or login."""
    request.session.pop('reset_password_email', None)
    return redirect('accounts:forgot_password')


def register_buyer_view(request):
    return redirect(f"{reverse('accounts:register')}?role=buyer")


def register_seller_view(request):
    return redirect(f"{reverse('accounts:register')}?role=seller")


@login_required
def profile_view(request):
    """View-only overview of user profile, saved delivery addresses, and account stats."""
    user = request.user
    profile, _ = BuyerProfile.objects.get_or_create(user=user)
    addresses = user.delivery_addresses.all()
    orders_count = user.orders.count() if hasattr(user, 'orders') else 0

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'addresses': addresses,
        'orders_count': orders_count,
    })


@login_required
def profile_edit_view(request):
    """Dedicated screen to edit ONLY personal contact details (Name and Phone)."""
    user = request.user

    if request.method == 'POST':
        form = PersonalDetailsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your personal details have been updated successfully.')
            return redirect('accounts:profile')
    else:
        form = PersonalDetailsForm(instance=user)

    orders_count = user.orders.count() if hasattr(user, 'orders') else 0

    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'orders_count': orders_count,
    })


@login_required
def address_add_view(request):
    """Dedicated screen to add a new delivery address."""
    user = request.user

    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user
            address.save()
            # If this is default, sync to legacy BuyerProfile
            if address.is_default:
                _sync_address_to_buyer_profile(user, address)
            messages.success(request, f"New address '{address.get_address_type_display()}' added successfully.")
            return redirect('accounts:profile')
    else:
        initial = {
            'full_name': user.full_name,
            'phone': user.phone or '',
            'state': 'Kerala',
            'is_default': not user.delivery_addresses.exists(),
        }
        form = DeliveryAddressForm(initial=initial)

    return render(request, 'accounts/address_form.html', {
        'form': form,
        'is_edit': False,
    })


@login_required
def address_edit_view(request, address_id):
    """Dedicated screen to edit an existing delivery address."""
    user = request.user
    address = get_object_or_404(DeliveryAddress, id=address_id, user=user)

    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST, instance=address)
        if form.is_valid():
            addr = form.save()
            if addr.is_default:
                _sync_address_to_buyer_profile(user, addr)
            messages.success(request, 'Delivery address updated successfully.')
            return redirect('accounts:profile')
    else:
        form = DeliveryAddressForm(instance=address)

    return render(request, 'accounts/address_form.html', {
        'form': form,
        'address': address,
        'is_edit': True,
    })


@login_required
def address_set_default_view(request, address_id):
    """Set an address as the default delivery destination."""
    user = request.user
    address = get_object_or_404(DeliveryAddress, id=address_id, user=user)
    address.is_default = True
    address.save()
    _sync_address_to_buyer_profile(user, address)
    messages.success(request, f"'{address.get_address_type_display()}' set as your default delivery address.")
    return redirect('accounts:profile')


@login_required
def address_delete_view(request, address_id):
    """Delete a delivery address."""
    user = request.user
    address = get_object_or_404(DeliveryAddress, id=address_id, user=user)
    was_default = address.is_default
    address_name = address.get_address_type_display()
    address.delete()

    # If deleted address was default, promote the first remaining address to default
    if was_default:
        first_rem = user.delivery_addresses.first()
        if first_rem:
            first_rem.is_default = True
            first_rem.save()
            _sync_address_to_buyer_profile(user, first_rem)

    messages.success(request, f"Address '{address_name}' has been deleted.")
    return redirect('accounts:profile')


def _sync_address_to_buyer_profile(user, address):
    """Sync default address details to BuyerProfile for backward compatibility."""
    try:
        bp, _ = BuyerProfile.objects.get_or_create(user=user)
        bp.shipping_address = address.street_address
        bp.city = address.city
        bp.state = address.state
        bp.postal_code = address.postal_code
        bp.landmark = address.landmark
        bp.alt_phone = address.alt_phone
        bp.save()
    except Exception:
        pass


def _redirect_by_role(user):
    if user.role == User.ROLE_ADMIN:
        return redirect('platform_admin:dashboard')
    elif user.role == User.ROLE_SELLER:
        return redirect('seller:dashboard')
    return redirect('marketplace:home')


@login_required
def view_verification_doc(request, pk):
    """
    Access-controlled endpoint to view/download seller KYC verification documents.
    Only accessible by the document owner or a platform admin.
    """
    seller = get_object_or_404(SellerProfile, pk=pk)
    is_owner = (hasattr(request.user, 'seller_profile') and request.user.seller_profile.pk == seller.pk)
    is_admin = (request.user.is_staff or getattr(request.user, 'role', '') == User.ROLE_ADMIN)

    if not (is_owner or is_admin):
        raise Http404("Document not found or access denied.")

    if not seller.verification_document:
        raise Http404("No verification document uploaded.")

    content_type, _ = mimetypes.guess_type(seller.verification_document.name)
    response = FileResponse(
        seller.verification_document.open('rb'),
        content_type=content_type or 'application/octet-stream'
    )
    # Add no-cache header to prevent intermediary caching of sensitive identity documents
    response['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    return response
