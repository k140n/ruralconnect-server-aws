"""Root URL configuration for RuralConnect."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('marketplace.urls')),
    path('', include('accounts.urls')),
    path('seller/', include('seller.urls')),
    path('admin-panel/', include('platform_admin.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
