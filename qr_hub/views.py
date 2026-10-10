import os
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import StoreInfo, SocialChannel, DynamicQRCode, QRScanLog, ButtonClickLog
from .serializers import (
    StoreInfoSerializer,
    SocialChannelSerializer,
    DynamicQRCodeSerializer,
    ButtonClickTrackSerializer,
)
from .qr_generator import generate_custom_qr_svg, generate_custom_qr_png


def detect_device_type(user_agent_string: str) -> str:
    """Classifies user agent into mobile, tablet, or desktop."""
    if not user_agent_string:
        return "unknown"
    ua = user_agent_string.lower()
    if "ipad" in ua or "tablet" in ua or ("android" in ua and "mobile" not in ua):
        return "tablet"
    elif "mobile" in ua or "iphone" in ua or "android" in ua or "phone" in ua:
        return "mobile"
    return "desktop"


def ensure_initial_seed():
    """Auto-seeds initial StoreInfo, Social Channels, and Dynamic QR code if DB is empty."""
    if not StoreInfo.objects.exists():
        StoreInfo.objects.create(
            name="Surya Teja Handloom Flagship Studio",
            badge_text="The Saree Store",
            hours_text="10:30 AM – 8:30 PM",
            open_time="10:30:00",
            close_time="20:30:00",
            timezone="Asia/Kolkata",
            address="Near Market Yard, Main Road, Gadwal - 509125, Telangana, India",
            phone_number="+919999999999",
            google_maps_url="https://www.google.com/maps/search/?api=1&query=Surya+Teja+Gadwal+Sarees",
            directions_button_text="Google Directions",
            is_active=True,
        )

    if not SocialChannel.objects.exists():
        default_channels = [
            {
                "channel_id": "official-website",
                "name": "OFFICIAL WEBSITE",
                "handle": "surya-teja-gadwal-sarees.vercel.app",
                "url": "https://surya-teja-gadwal-sarees.vercel.app",
                "icon_name": "Globe",
                "color": "#E5A93C",
                "accent_color": "#D4AF37",
                "description": "Explore our latest saree catalog, bridal silk collections, and order online with worldwide shipping.",
                "button_label": "Visit Online Store",
                "is_verified": True,
                "is_featured": True,
                "order": 1,
            },
            {
                "channel_id": "whatsapp-channel",
                "name": "WHATSAPP CHANNEL",
                "handle": "Surya Teja Handlooms VIP",
                "url": "https://whatsapp.com/channel/0029Va9xyzSuryaTeja",
                "icon_name": "WhatsApp",
                "color": "#25D366",
                "accent_color": "#128C7E",
                "description": "Join our exclusive VIP WhatsApp Channel for first-look saree previews, flash discounts & instant drops.",
                "button_label": "Join WhatsApp Channel",
                "is_verified": True,
                "is_featured": True,
                "order": 2,
            },
            {
                "channel_id": "instagram",
                "name": "INSTAGRAM",
                "handle": "@suryatejagadwalsaree",
                "url": "https://www.instagram.com/suryatejagadwalsaree/",
                "icon_name": "Instagram",
                "color": "#E1306C",
                "accent_color": "#F56040",
                "description": "Daily saree drapes, behind-the-loom reels, artisan weaver stories, and exclusive bridal drops.",
                "button_label": "Follow on Instagram",
                "is_verified": True,
                "is_featured": False,
                "order": 3,
            },
            {
                "channel_id": "youtube",
                "name": "YOUTUBE",
                "handle": "@suryatejagadwalsarees",
                "url": "https://www.youtube.com/@suryatejagadwalsarees",
                "icon_name": "Youtube",
                "color": "#FF0000",
                "accent_color": "#CC0000",
                "description": "4K Weaving masterclasses, authentic loom walkthroughs, saree drape tutorials & customer showcase films.",
                "button_label": "Watch on YouTube",
                "is_verified": True,
                "is_featured": False,
                "order": 4,
            },
            {
                "channel_id": "google-review",
                "name": "GOOGLE MAPS RATING",
                "handle": "Surya Teja Gadwal Sarees",
                "url": "https://maps.google.com/?q=Surya+Teja+Gadwal+Sarees",
                "icon_name": "MapPin",
                "color": "#4285F4",
                "accent_color": "#34A853",
                "description": "Share your shopping feedback and rate us 5 stars on Google Maps to support our authentic handloom artisans.",
                "button_label": "Rate on Google Maps",
                "is_verified": True,
                "is_featured": False,
                "order": 5,
            },
            {
                "channel_id": "pinterest",
                "name": "PINTEREST",
                "handle": "Surya Teja Handlooms",
                "url": "https://pinterest.com/suryatejahandlooms",
                "icon_name": "Pinterest",
                "color": "#E60023",
                "accent_color": "#AD081B",
                "description": "Curated bridal color moodboards, heirloom saree styling pairings, blouse inspirations and drape aesthetics.",
                "button_label": "View on Pinterest",
                "is_verified": False,
                "is_featured": False,
                "order": 6,
            },
            {
                "channel_id": "facebook",
                "name": "FACEBOOK",
                "handle": "Surya Teja Sarees & Silks",
                "url": "https://facebook.com/suryatejasarees",
                "icon_name": "Facebook",
                "color": "#1877F2",
                "accent_color": "#0C5DC7",
                "description": "Join our family of 80,000+ handloom enthusiasts. Live interactive auctions, customer reviews and updates.",
                "button_label": "Join on Facebook",
                "is_verified": True,
                "is_featured": False,
                "order": 7,
            },
        ]
        for c_data in default_channels:
            SocialChannel.objects.create(**c_data)

    if not DynamicQRCode.objects.exists():
        DynamicQRCode.objects.create(
            slug="hub",
            title="Surya Teja Official Hub QR",
            target_type="landing_page",
            fg_color="#18181A",
            bg_color="#FFFFFF",
            include_logo=True,
            is_active=True,
        )


class HubDataView(APIView):
    """
    GET /api/hub/data/
    Provides complete dynamic configuration for the frontend hub:
    - Store address, hours, status, phone number, directions URL
    - Ordered social channel cards with active styling and button labels
    - Dynamic QR routing info
    - Profile brand meta
    """
    permission_classes = [AllowAny]

    def get(self, request):
        ensure_initial_seed()

        store = StoreInfo.objects.filter(is_active=True).order_by('-updated_at').first()
        channels = SocialChannel.objects.filter(is_active=True).order_by('order', 'created_at')
        active_qr = DynamicQRCode.objects.filter(is_active=True, slug="hub").first() or DynamicQRCode.objects.filter(is_active=True).first()

        context = {'request': request}
        data = {
            "success": True,
            "store": StoreInfoSerializer(store).data if store else None,
            "channels": SocialChannelSerializer(channels, many=True).data,
            "active_qr": DynamicQRCodeSerializer(active_qr, context=context).data if active_qr else None,
            "profile": {
                "name": "Surya Teja Handlooms",
                "tagline": "Official Social Media & Connect Hub",
                "monogram": "ST",
                "verified": True,
                "logo_url": "/st_logo.png",
            },
            "timestamp": timezone.now().isoformat(),
        }
        return Response(data, status=status.HTTP_200_OK)


def dynamic_qr_redirect_view(request, slug):
    """
    GET /r/<slug>/ or /api/r/<slug>/
    Dynamic QR Code redirect with analytics logging.
    Scans hit this endpoint, get recorded in QRScanLog, and 302 redirect to the destination.
    """
    ensure_initial_seed()
    qr_obj = get_object_or_404(DynamicQRCode, slug=slug, is_active=True)

    # 1. Track scan analytics
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    ip_addr = request.META.get('REMOTE_ADDR', '')
    referrer = request.META.get('HTTP_REFERER', '')
    device = detect_device_type(user_agent)

    QRScanLog.objects.create(
        qr=qr_obj,
        ip_address=ip_addr,
        user_agent=user_agent,
        device_type=device,
        referrer=referrer
    )

    # 2. Update QR object counters
    qr_obj.scan_count += 1
    qr_obj.last_scanned_at = timezone.now()
    qr_obj.save(update_fields=['scan_count', 'last_scanned_at'])

    # 3. Resolve destination URL & Redirect
    destination = qr_obj.get_destination_url(request)
    return HttpResponseRedirect(destination)


def dynamic_qr_image_view(request, slug=None):
    """
    GET /api/hub/qr/image/ or /api/hub/qr/<slug>/image/
    Renders and streams the custom dynamic circular/orbit QR code image.
    Query parameters:
    - format: 'svg' (default) or 'png'
    - slug: 'hub' (default)
    - size: integer dimension (default 600 for svg, 1000 for png)
    - fg: hex color (default '#18181A')
    - bg: hex color (default '#FFFFFF')
    - logo: bool (default 1)
    """
    ensure_initial_seed()
    slug = slug or request.GET.get('slug', 'hub')
    qr_obj = DynamicQRCode.objects.filter(slug=slug, is_active=True).first()

    # Resolve the data/URL to be encoded inside the QR matrix
    mode_param = request.GET.get('mode')
    if qr_obj:
        if mode_param == 'direct':
            qr_data = qr_obj.get_destination_url(request)
        elif mode_param == 'dynamic':
            qr_data = request.build_absolute_uri(f"/r/{qr_obj.slug}/")
        else:
            qr_data = qr_obj.get_encoded_data(request)

        fg_color = request.GET.get('fg', qr_obj.fg_color)
        bg_color = request.GET.get('bg', qr_obj.bg_color)
        include_logo = request.GET.get('logo', str(int(qr_obj.include_logo))) in ['1', 'true', 'True']
    else:
        qr_data = request.GET.get('url') or request.GET.get('data') or request.build_absolute_uri('/')
        fg_color = request.GET.get('fg', '#18181A')
        bg_color = request.GET.get('bg', '#FFFFFF')
        include_logo = request.GET.get('logo', '1') in ['1', 'true', 'True']

    img_format = request.GET.get('format', 'svg').lower()

    if img_format == 'png':
        size = int(request.GET.get('size', 1000))
        logo_path = None
        if include_logo:
            candidates = [
                os.path.join(settings.BASE_DIR, '..', 'teja_QR', 'public', 'st_logo.png'),
                os.path.join(settings.BASE_DIR, '..', 'teja_QR', 'src', 'assets', 'st_logo.png'),
            ]
            for p in candidates:
                if os.path.exists(p):
                    logo_path = p
                    break

        png_bytes = generate_custom_qr_png(
            data=qr_data,
            fg_color=fg_color,
            bg_color=bg_color,
            size=size,
            logo_path=logo_path
        )
        response = HttpResponse(png_bytes, content_type='image/png')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    else:
        size = int(request.GET.get('size', 600))
        svg_content = generate_custom_qr_svg(
            data=qr_data,
            fg_color=fg_color,
            bg_color=bg_color,
            size=size,
            include_orbit=True
        )
        response = HttpResponse(svg_content, content_type='image/svg+xml; charset=utf-8')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class TrackClickView(APIView):
    """
    POST /api/hub/track-click/
    Logs clicks on Directions, Call, Copy Address, or Social Channel cards.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ButtonClickTrackSerializer(data=request.data)
        if serializer.is_valid():
            b_type = serializer.validated_data['button_type']
            c_id = serializer.validated_data.get('channel_id', '')

            ButtonClickLog.objects.create(
                button_type=b_type,
                channel_id=c_id,
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            # Increment counter on channel if applicable
            if c_id and b_type.startswith('social_'):
                SocialChannel.objects.filter(channel_id=c_id).update(
                    click_count=models.F('click_count') + 1
                )

            return Response({"success": True, "tracked": b_type}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HubAnalyticsSummaryView(APIView):
    """
    GET /api/hub/analytics/
    Admin / Dashboard analytics summary.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        total_scans = QRScanLog.objects.count()
        total_clicks = ButtonClickLog.objects.count()
        qr_codes = DynamicQRCode.objects.all().values('slug', 'title', 'scan_count', 'last_scanned_at')
        channels = SocialChannel.objects.all().values('channel_id', 'name', 'click_count')

        # Device breakdown
        devices = {}
        for dev in QRScanLog.objects.values_list('device_type', flat=True):
            devices[dev] = devices.get(dev, 0) + 1

        return Response({
            "total_scans": total_scans,
            "total_clicks": total_clicks,
            "devices": devices,
            "qr_codes": list(qr_codes),
            "channels": list(channels),
        }, status=status.HTTP_200_OK)


def render_glass_error_response(request, status_code: int, badge_text: str, title_text: str, desc_text: str):
    """
    Renders a unified, glassy error response.
    Returns JSON for API calls or rich responsive HTML for browser pages,
    ensuring zero leakage of sensitive stack traces or internal server details.
    """
    is_api = request.path.startswith('/api/') or 'application/json' in request.META.get('HTTP_ACCEPT', '')
    if is_api:
        return JsonResponse({
            "success": False,
            "status_code": status_code,
            "error": title_text,
            "message": desc_text
        }, status=status_code)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_code} - {title_text} | Surya Teja</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #F3F4F6 0%, #E5E7EB 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            color: #18181A;
            overflow-x: hidden;
            position: relative;
        }}
        .orb {{
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            pointer-events: none;
            z-index: 1;
        }}
        .orb-1 {{ width: 350px; height: 350px; background: rgba(139, 92, 246, 0.2); top: 10%; left: 15%; }}
        .orb-2 {{ width: 380px; height: 380px; background: rgba(184, 151, 104, 0.2); bottom: 10%; right: 15%; }}
        .glass-card {{
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 520px;
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(28px) saturate(160%);
            -webkit-backdrop-filter: blur(28px) saturate(160%);
            border: 1px solid rgba(255, 255, 255, 0.9);
            border-top: 1px solid rgba(255, 255, 255, 1);
            border-radius: 32px;
            padding: 40px 32px;
            text-align: center;
            box-shadow: inset 0 1px 2px rgba(255,255,255,0.9), 0 24px 48px -12px rgba(0, 0, 0, 0.15);
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.9);
            font-size: 11px;
            font-weight: 700;
            color: #4B5563;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }}
        h1 {{
            font-family: 'Playfair Display', serif;
            font-size: 64px;
            font-weight: 700;
            line-height: 1;
            color: #111827;
            margin-bottom: 6px;
        }}
        .subtitle {{
            font-size: 17px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 16px;
        }}
        .desc {{
            font-size: 13px;
            color: #6B7280;
            line-height: 1.6;
            margin-bottom: 24px;
        }}
        .svg-container {{
            width: 100%;
            height: 170px;
            margin-bottom: 18px;
        }}
        .btn-group {{
            display: flex;
            gap: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 24px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            text-decoration: none;
            transition: all 0.2s ease;
            cursor: pointer;
        }}
        .btn-primary {{
            background: #18181A;
            color: #FFFFFF;
            border: 1px solid #18181A;
            box-shadow: 0 4px 14px rgba(0,0,0,0.15);
        }}
        .btn-primary:hover {{
            background: #000000;
            transform: translateY(-2px);
        }}
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.7);
            color: #374151;
            border: 1px solid rgba(255, 255, 255, 0.9);
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.95);
            transform: translateY(-2px);
        }}
        @keyframes spark {{
            0%, 100% {{ opacity: 0.3; transform: scale(0.95); }}
            50% {{ opacity: 1; transform: scale(1.1); }}
        }}
        .spark-pulse {{
            animation: spark 1.2s infinite ease-in-out;
            transform-origin: center;
        }}
    </style>
</head>
<body>
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="glass-card">
        <div class="badge">{badge_text}</div>
        <h1>{status_code}</h1>
        <div class="subtitle">{title_text}</div>

        <div class="svg-container">
            <svg viewBox="0 0 500 220" width="100%" height="100%" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M 20 170 C 60 200, 80 130, 120 140 C 160 150, 170 100, 210 105" stroke="#8B5CF6" stroke-width="5" stroke-linecap="round" fill="none"/>
                <rect x="206" y="88" width="34" height="34" rx="8" fill="#7C3AED"/>
                <rect x="236" y="92" width="8" height="26" rx="3" fill="#6D28D9"/>
                <circle cx="120" cy="70" r="18" fill="#4B5563"/>
                <path d="M 100 125 C 100 95, 140 95, 140 125 Z" fill="#6B7280"/>
                <path d="M 135 105 Q 175 95, 206 105" stroke="#6B7280" stroke-width="7" stroke-linecap="round"/>

                <rect x="264" y="88" width="34" height="34" rx="8" fill="#7C3AED"/>
                <rect x="250" y="94" width="14" height="6" rx="2" fill="#D4AF37"/>
                <rect x="250" y="110" width="14" height="6" rx="2" fill="#D4AF37"/>
                <path d="M 298 105 C 340 100, 360 170, 400 140 C 440 120, 460 180, 480 170" stroke="#8B5CF6" stroke-width="5" stroke-linecap="round" fill="none"/>
                <circle cx="380" cy="80" r="18" fill="#4B5563"/>
                <path d="M 360 135 C 360 115, 400 115, 400 135 Z" fill="#6B7280"/>
                <path d="M 365 115 Q 325 100, 298 105" stroke="#6B7280" stroke-width="7" stroke-linecap="round"/>

                <g class="spark-pulse">
                    <path d="M 246 82 L 254 95 L 244 102 L 256 122 L 248 128" stroke="#F59E0B" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                </g>
            </svg>
        </div>

        <p class="desc">{desc_text}</p>
        <div class="btn-group">
            <a href="/" class="btn btn-primary">Back to Home</a>
            <button onclick="window.history.back()" class="btn btn-secondary">Go Back</button>
        </div>
    </div>
</body>
</html>"""
    return HttpResponse(html_content, status=status_code)


def custom_404_view(request, exception=None):
    return render_glass_error_response(
        request,
        404,
        "✦ 404 • Resource Not Found",
        "Page Not Found",
        "The page or resource you are looking for doesn't exist, has been removed, or the link is broken."
    )


def custom_500_view(request):
    return render_glass_error_response(
        request,
        500,
        "✦ 500 • Internal Server Error",
        "Server Error Encountered",
        "Our backend servers encountered an internal error. Our team has been notified. Please try again shortly."
    )


def custom_403_view(request, exception=None):
    return render_glass_error_response(
        request,
        403,
        "✦ 403 • Access Forbidden",
        "Access Restricted",
        "You do not have permission to access the requested resource."
    )


def custom_400_view(request, exception=None):
    return render_glass_error_response(
        request,
        400,
        "✦ 400 • Bad Request",
        "Invalid Request",
        "The server could not understand or process your request due to invalid syntax or parameters."
    )


