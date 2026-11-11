"""Custom middlewares for RuralConnect."""

class PreventBackCacheMiddleware:
    """
    Prevents browsers from caching sensitive authenticated views.
    Ensures that clicking the Back button after logout forces a re-fetch
    rather than showing stale, sensitive cached pages from bfcache.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        is_sensitive = (
            request.user.is_authenticated or
            any(request.path.startswith(p) for p in ['/admin-panel', '/seller', '/cart', '/checkout', '/login'])
        )
        if is_sensitive:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
