from django.db import models
from django.utils.text import slugify
from django.conf import settings
import uuid


class StoreInfo(models.Model):
    """Configuration for Store Location & Actions on the QR Landing Page."""
    name = models.CharField(
        max_length=255,
        default="Surya Teja Handloom Flagship Studio",
        help_text="Store or studio name"
    )
    badge_text = models.CharField(
        max_length=100,
        default="Open Studio & Flagship",
        help_text="Status badge (e.g. Open Studio & Flagship)"
    )
    hours_text = models.CharField(
        max_length=100,
        default="10:30 AM – 8:30 PM",
        help_text="Operating hours text representation"
    )
    open_time = models.TimeField(
        default="10:30:00",
        help_text="Store opening time in IST (e.g. 10:30:00)"
    )
    close_time = models.TimeField(
        default="20:30:00",
        help_text="Store closing time in IST (e.g. 20:30:00)"
    )
    timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata",
        help_text="Base timezone for store operating hours (default IST: Asia/Kolkata)"
    )
    address = models.TextField(
        default="Near Market Yard, Main Road, Gadwal - 509125, Telangana, India",
        help_text="Complete store address"
    )
    phone_number = models.CharField(
        max_length=50,
        default="+919999999999",
        help_text="Direct phone number for call button"
    )
    google_maps_url = models.URLField(
        max_length=500,
        default="https://www.google.com/maps/search/?api=1&query=Surya+Teja+Gadwal+Sarees",
        help_text="Google Maps Directions URL"
    )
    directions_button_text = models.CharField(
        max_length=50,
        default="Google Directions"
    )
    WEEKDAY_CHOICES = [
        ('none', 'No Weekly Off'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    weekly_off_day = models.CharField(
        max_length=20,
        choices=WEEKDAY_CHOICES,
        default='none',
        help_text="Weekly off day — store shows as Closed or runs custom off-day hours on this day"
    )
    weekly_off_open_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Store opening time on weekly off day in IST (e.g. 11:00:00). Leave empty if closed all day."
    )
    weekly_off_close_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Store closing time on weekly off day in IST (e.g. 16:00:00). Leave empty if closed all day."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this store info is currently displayed"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store Information"
        verbose_name_plural = "Store Information"

    def get_hours_display(self):
        if self.open_time and self.close_time:
            try:
                open_str = self.open_time.strftime("%I:%M %p").lstrip("0")
                close_str = self.close_time.strftime("%I:%M %p").lstrip("0")
                return f"{open_str} – {close_str}"
            except Exception:
                pass
        return self.hours_text

    def get_weekly_off_hours_display(self):
        if self.weekly_off_open_time and self.weekly_off_close_time:
            try:
                open_str = self.weekly_off_open_time.strftime("%I:%M %p").lstrip("0")
                close_str = self.weekly_off_close_time.strftime("%I:%M %p").lstrip("0")
                return f"{open_str} – {close_str}"
            except Exception:
                pass
        return None

    def __str__(self):
        return f"{self.name} ({self.get_hours_display()})"


class SocialChannel(models.Model):
    """Dynamic Social Media Channels & Action Cards displayed in the hub."""
    ICON_CHOICES = [
        ('Globe', 'Website / Globe'),
        ('WhatsApp', 'WhatsApp Channel / Chat'),
        ('Instagram', 'Instagram'),
        ('Youtube', 'YouTube'),
        ('MapPin', 'Google Review / MapPin'),
        ('Pinterest', 'Pinterest'),
        ('Facebook', 'Facebook'),
        ('Twitter', 'Twitter / X'),
        ('Linkedin', 'LinkedIn'),
        ('Phone', 'Phone Call'),
        ('Mail', 'Email'),
    ]

    channel_id = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique identifier (e.g. official-website, instagram, etc.)"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display title (e.g. Official Website, WhatsApp Channel)"
    )
    handle = models.CharField(
        max_length=100,
        help_text="Handle or subtitle (e.g. @suryatejagadwalsaree)"
    )
    url = models.URLField(
        max_length=500,
        help_text="Target URL to open when clicking the card action"
    )
    icon_name = models.CharField(
        max_length=50,
        choices=ICON_CHOICES,
        default='Globe',
        help_text="Icon to render for this card"
    )
    color = models.CharField(
        max_length=30,
        default="#D4AF37",
        help_text="Primary hex color (e.g. #25D366 for WhatsApp)"
    )
    accent_color = models.CharField(
        max_length=30,
        default="#B89768",
        help_text="Accent hex color for gradient"
    )
    description = models.TextField(
        blank=True,
        help_text="Short card description text"
    )
    button_label = models.CharField(
        max_length=50,
        default="Visit",
        help_text="Label on the primary action button"
    )
    is_verified = models.BooleanField(
        default=True,
        help_text="Display verified badge on card"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Highlight or feature this channel"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Ordering position in the grid (lower numbers appear first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle channel visibility"
    )
    click_count = models.PositiveIntegerField(
        default=0,
        help_text="Total recorded clicks/visits"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Social Channel Card"
        verbose_name_plural = "Social Channel Cards"

    def __str__(self):
        return f"{self.name} ({self.handle})"


class DynamicQRCode(models.Model):
    """Dynamic QR Code configuration with short-link routing and tracking."""
    TARGET_TYPE_CHOICES = [
        ('landing_page', 'QR Hub Landing Page'),
        ('google_maps', 'Google Maps Directions'),
        ('whatsapp', 'WhatsApp VIP Channel / Chat'),
        ('website', 'Official Website Store'),
        ('instagram', 'Instagram Profile'),
        ('custom_url', 'Custom External URL'),
    ]

    slug = models.SlugField(
        max_length=64,
        unique=True,
        help_text="Short identifier in dynamic redirect URL (e.g. 'hub', 'flagship', 'insta')"
    )
    title = models.CharField(
        max_length=200,
        default="Surya Teja Official Hub QR"
    )
    target_type = models.CharField(
        max_length=50,
        choices=TARGET_TYPE_CHOICES,
        default='landing_page'
    )
    ENCODE_MODE_CHOICES = [
        ('direct', 'Direct Target URL (Encodes Destination Directly - Opens Instantly)'),
        ('dynamic', 'Dynamic Redirect URL (/r/<slug>/ - Tracks Scans)'),
    ]

    encode_mode = models.CharField(
        max_length=30,
        choices=ENCODE_MODE_CHOICES,
        default='direct',
        help_text="Direct encodes the actual destination URL into the QR. Dynamic uses a short redirect."
    )
    custom_target_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Custom destination URL if target_type is custom_url or overridden"
    )
    fg_color = models.CharField(
        max_length=30,
        default="#18181A",
        help_text="Foreground/QR module color"
    )
    bg_color = models.CharField(
        max_length=30,
        default="#FFFFFF",
        help_text="Background color"
    )
    include_logo = models.BooleanField(
        default=True,
        help_text="Embed ST brand logo in center of QR code"
    )
    scan_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of scans tracked"
    )
    last_scanned_at = models.DateTimeField(
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle active state of dynamic redirection"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dynamic QR Code"
        verbose_name_plural = "Dynamic QR Codes"

    def __str__(self):
        return f"{self.title} ({self.get_destination_url()})"

    def get_destination_url(self, request=None):
        """Resolves the current dynamic destination URL."""
        if self.custom_target_url:
            return self.custom_target_url

        frontend_base = getattr(settings, 'FRONTEND_URL', 'https://surya-teja-gadwal-sarees.vercel.app')
        if self.target_type == 'landing_page':
            return f"{frontend_base}/"
        elif self.target_type == 'google_maps':
            store = StoreInfo.objects.filter(is_active=True).first()
            return store.google_maps_url if store else "https://www.google.com/maps/search/?api=1&query=Surya+Teja+Gadwal+Sarees"
        elif self.target_type == 'whatsapp':
            channel = SocialChannel.objects.filter(channel_id='whatsapp-channel', is_active=True).first()
            return channel.url if channel else f"https://wa.me/{getattr(settings, 'WHATSAPP_NUMBER', '919999999999')}"
        elif self.target_type == 'website':
            channel = SocialChannel.objects.filter(channel_id='official-website', is_active=True).first()
            return channel.url if channel else "https://surya-teja-gadwal-sarees.vercel.app"
        elif self.target_type == 'instagram':
            channel = SocialChannel.objects.filter(channel_id='instagram', is_active=True).first()
            return channel.url if channel else "https://www.instagram.com/suryatejagadwalsaree/"
        
        return f"{frontend_base}/"

    def get_encoded_data(self, request=None):
        """Returns the actual string or URL that is encoded into the QR code matrix."""
        # If set to direct or if custom_url is chosen, use the destination URL directly
        if self.encode_mode == 'direct' or self.target_type == 'custom_url':
            return self.get_destination_url(request)
        
        # Dynamic short-link redirect mode
        base_url = getattr(settings, 'DYNAMIC_QR_BASE_URL', None)
        if not base_url and request:
            base_url = request.build_absolute_uri('/')[:-1]
        if not base_url:
            base_url = getattr(settings, 'FRONTEND_URL', 'https://surya-teja-gadwal-sarees.vercel.app')
        return f"{base_url}/r/{self.slug}/"


class QRScanLog(models.Model):
    """Detailed analytics log for every dynamic QR code scan."""
    qr = models.ForeignKey(
        DynamicQRCode,
        on_delete=models.CASCADE,
        related_name='scans'
    )
    scanned_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, default="unknown")
    referrer = models.TextField(blank=True)

    class Meta:
        ordering = ['-scanned_at']
        verbose_name = "QR Scan Log"
        verbose_name_plural = "QR Scan Logs"

    def __str__(self):
        return f"Scan for {self.qr.slug} at {self.scanned_at} ({self.device_type})"


class ButtonClickLog(models.Model):
    """User interaction analytics on the landing page."""
    BUTTON_TYPE_CHOICES = [
        ('directions', 'Directions Button'),
        ('call', 'Call Phone Button'),
        ('copy_address', 'Copy Address Button'),
        ('social_visit', 'Social Channel Visit'),
        ('social_copy', 'Social Channel Copy'),
        ('social_share', 'Social Channel Share'),
        ('qr_modal_open', 'QR Modal Open'),
    ]

    button_type = models.CharField(max_length=50, choices=BUTTON_TYPE_CHOICES)
    channel_id = models.CharField(max_length=100, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ['-clicked_at']
        verbose_name = "Button Click Log"
        verbose_name_plural = "Button Click Logs"

    def __str__(self):
        return f"{self.button_type} ({self.channel_id}) at {self.clicked_at}"
