"""Security utility functions for RuralConnect."""

from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_redirect_url(request, next_url, fallback_url):
    """
    Validate that next_url points to a safe internal URL on the current host.
    Prevents Open Redirect attacks.
    """
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return next_url
    return fallback_url

