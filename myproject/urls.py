from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response({"status": "ok", "message": "Backend is active"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health_check"),
    path("api/", include("products.urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("consultations.urls")),
    path("", include("qr_hub.urls")),
]

admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Handloom Administration")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Handloom Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Welcome to Admin Dashboard")

if getattr(settings, "DEMO_MODE", False):
    admin.site.disable_action("delete_selected")

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'qr_hub.views.custom_404_view'
handler500 = 'qr_hub.views.custom_500_view'
handler403 = 'qr_hub.views.custom_403_view'
handler400 = 'qr_hub.views.custom_400_view'
