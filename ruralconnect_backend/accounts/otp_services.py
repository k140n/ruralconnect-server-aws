"""OTP generation, email dispatching, and verification services for RuralConnect."""

import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import EmailVerificationOTP

OTP_EXPIRY_MINUTES = 10
RESEND_COOLDOWN_SECONDS = 60
MAX_VERIFICATION_ATTEMPTS = 5


def get_resend_cooldown_seconds(email):
    """Return remaining cooldown seconds before a new OTP can be requested."""
    latest_otp = EmailVerificationOTP.objects.filter(email=email).order_by('-created_at').first()
    if not latest_otp:
        return 0
    elapsed = (timezone.now() - latest_otp.created_at).total_seconds()
    remaining = int(RESEND_COOLDOWN_SECONDS - elapsed)
    return max(0, remaining)


def generate_and_send_otp(email, user_name='Valued User'):
    """
    Generate a 6-digit OTP and send via email.
    Enforces a 60-second resend cooldown.
    Returns (success: bool, message: str, remaining_cooldown: int).
    """
    remaining = get_resend_cooldown_seconds(email)
    if remaining > 0:
        return False, f"Please wait {remaining} seconds before requesting a new code.", remaining

    # Generate 6-digit cryptographically secure code
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Invalidate previous unverified OTPs for this email
    EmailVerificationOTP.objects.filter(email=email, is_verified=False).delete()

    # Create new record
    otp_record = EmailVerificationOTP.objects.create(
        email=email,
        otp_code=code,
        expires_at=expires_at
    )

    # Prepare email context
    subject = f"{code} is your RuralConnect verification code"
    context = {
        'otp_code': code,
        'user_name': user_name or 'Valued User',
        'valid_minutes': OTP_EXPIRY_MINUTES,
        'site_name': 'RuralConnect',
    }

    html_content = render_to_string('emails/otp_verification.html', context)
    text_content = (
        f"Hello {user_name},\n\n"
        f"Your RuralConnect verification code is: {code}\n\n"
        f"This code will expire in {OTP_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"— The RuralConnect Team"
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'RuralConnect <onboarding@resend.dev>')
    msg = EmailMultiAlternatives(subject, text_content, from_email, [email])
    msg.attach_alternative(html_content, "text/html")
    
    if settings.DEBUG:
        print("\n" + "="*64)
        print(f"📧 [RURALCONNECT SIGNUP OTP NOTICE]")
        print(f"    To: {email}")
        print(f"    🔑 Verification Code: {code}")
        print("="*64 + "\n")

    try:
        msg.send()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to deliver email via SMTP to {email}: {e}")

    return True, "Verification code sent successfully.", RESEND_COOLDOWN_SECONDS


def generate_and_send_reset_otp(email, user_name='Valued User'):
    """
    Generate a 6-digit OTP and send via email for password reset.
    Enforces a 60-second resend cooldown.
    Returns (success: bool, message: str, remaining_cooldown: int).
    """
    remaining = get_resend_cooldown_seconds(email)
    if remaining > 0:
        return False, f"Please wait {remaining} seconds before requesting a new code.", remaining

    # Generate 6-digit cryptographically secure code
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    # Invalidate previous unverified OTPs for this email
    EmailVerificationOTP.objects.filter(email=email, is_verified=False).delete()

    # Create new record
    EmailVerificationOTP.objects.create(
        email=email,
        otp_code=code,
        expires_at=expires_at
    )

    # Prepare email context
    subject = f"{code} is your RuralConnect password reset code"
    context = {
        'otp_code': code,
        'user_name': user_name or 'Valued User',
        'valid_minutes': OTP_EXPIRY_MINUTES,
        'site_name': 'RuralConnect',
    }

    html_content = render_to_string('emails/password_reset_otp.html', context)
    text_content = (
        f"Hello {user_name},\n\n"
        f"Your RuralConnect password reset code is: {code}\n\n"
        f"This code will expire in {OTP_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"— The RuralConnect Team"
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'RuralConnect <onboarding@resend.dev>')
    msg = EmailMultiAlternatives(subject, text_content, from_email, [email])
    msg.attach_alternative(html_content, "text/html")

    if settings.DEBUG:
        print("\n" + "="*64)
        print(f"📧 [RURALCONNECT PASSWORD RESET OTP NOTICE]")
        print(f"    To: {email}")
        print(f"    🔑 Password Reset Code: {code}")
        print("="*64 + "\n")

    try:
        msg.send()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to deliver password reset email via SMTP to {email}: {e}")

    return True, "Password reset code sent successfully.", RESEND_COOLDOWN_SECONDS


def verify_email_otp(email, submitted_code):
    """
    Verify the entered OTP against the database.
    Returns (is_valid: bool, error_message: str).
    """
    if not submitted_code or not submitted_code.strip().isdigit() or len(submitted_code.strip()) != 6:
        return False, "Please enter a valid 6-digit numeric verification code."

    code = submitted_code.strip()
    otp_record = EmailVerificationOTP.objects.filter(email=email, is_verified=False).order_by('-created_at').first()

    if not otp_record:
        return False, "No active verification code found. Please request a new one."

    if timezone.now() > otp_record.expires_at:
        return False, "This verification code has expired. Please request a new code."

    if otp_record.attempts >= MAX_VERIFICATION_ATTEMPTS:
        return False, "Too many failed attempts. For your security, please request a new verification code."

    if not secrets.compare_digest(str(otp_record.otp_code), str(code)):
        otp_record.attempts += 1
        otp_record.save(update_fields=['attempts'])
        remaining_attempts = MAX_VERIFICATION_ATTEMPTS - otp_record.attempts
        if remaining_attempts > 0:
            return False, f"Incorrect code. You have {remaining_attempts} attempt{'s' if remaining_attempts > 1 else ''} remaining."
        return False, "Incorrect code. Maximum attempts reached. Please request a new code."

    # Code is valid! Mark as verified
    otp_record.is_verified = True
    otp_record.save(update_fields=['is_verified'])
    return True, "Email verified successfully."
