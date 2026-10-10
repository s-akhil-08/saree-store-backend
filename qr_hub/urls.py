from django.urls import path
from .views import (
    HubDataView,
    dynamic_qr_redirect_view,
    dynamic_qr_image_view,
    TrackClickView,
    HubAnalyticsSummaryView,
)

urlpatterns = [
    # Full landing page dynamic data (Store info, Social channels, Active QR)
    path('api/hub/data/', HubDataView.as_view(), name='hub_data'),

    # Custom Dynamic QR Image Generation (SVG / PNG stream)
    path('api/hub/qr/image/', dynamic_qr_image_view, name='hub_qr_image_default'),
    path('api/hub/qr/<slug:slug>/image/', dynamic_qr_image_view, name='hub_qr_image'),

    # Dynamic QR Code Redirect with analytics tracking (/r/<slug>/)
    path('r/<slug:slug>/', dynamic_qr_redirect_view, name='qr_redirect'),
    path('api/r/<slug:slug>/', dynamic_qr_redirect_view, name='qr_redirect_api'),

    # Interaction & click analytics tracking
    path('api/hub/track-click/', TrackClickView.as_view(), name='hub_track_click'),

    # Analytics summary
    path('api/hub/analytics/', HubAnalyticsSummaryView.as_view(), name='hub_analytics'),
]
