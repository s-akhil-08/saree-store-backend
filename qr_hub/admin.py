from django import forms
from datetime import time
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from adminsortable2.admin import SortableAdminMixin
from .models import StoreInfo, SocialChannel, DynamicQRCode, QRScanLog, ButtonClickLog

HOUR_CHOICES = [
    (0, "12:00 AM Midnight (00:00)"),
    (1, "01:00 AM (01:00)"),
    (2, "02:00 AM (02:00)"),
    (3, "03:00 AM (03:00)"),
    (4, "04:00 AM (04:00)"),
    (5, "05:00 AM (05:00)"),
    (6, "06:00 AM (06:00)"),
    (7, "07:00 AM (07:00)"),
    (8, "08:00 AM (08:00)"),
    (9, "09:00 AM (09:00)"),
    (10, "10:00 AM (10:00)"),
    (11, "11:00 AM (11:00)"),
    (12, "12:00 PM Noon (12:00)"),
    (13, "01:00 PM (13:00)"),
    (14, "02:00 PM (14:00)"),
    (15, "03:00 PM (15:00)"),
    (16, "04:00 PM (16:00)"),
    (17, "05:00 PM (17:00)"),
    (18, "06:00 PM (18:00)"),
    (19, "07:00 PM (19:00)"),
    (20, "08:00 PM (20:00)"),
    (21, "09:00 PM (21:00)"),
    (22, "10:00 PM (22:00)"),
    (23, "11:00 PM (23:00)"),
]

MINUTE_CHOICES = [(m, f"{m:02d} mins") for m in range(0, 60, 5)]


class StoreInfoAdminForm(forms.ModelForm):
    open_hour = forms.TypedChoiceField(
        choices=HOUR_CHOICES,
        coerce=int,
        label="Open Hour (12h / 24h)",
        initial=10,
        help_text="Select store opening hour"
    )
    open_minute = forms.TypedChoiceField(
        choices=MINUTE_CHOICES,
        coerce=int,
        label="Open Minute",
        initial=30,
        help_text="Select store opening minute"
    )
    close_hour = forms.TypedChoiceField(
        choices=HOUR_CHOICES,
        coerce=int,
        label="Close Hour (12h / 24h)",
        initial=20,
        help_text="Select store closing hour"
    )
    close_minute = forms.TypedChoiceField(
        choices=MINUTE_CHOICES,
        coerce=int,
        label="Close Minute",
        initial=30,
        help_text="Select store closing minute"
    )

    # Weekly Off Schedule Selection
    weekly_off_schedule_type = forms.ChoiceField(
        choices=[
            ('closed_all_day', 'Closed All Day (Default)'),
            ('custom_hours', 'Open for Custom Hours on Weekly Off (Select Below)'),
        ],
        label="Off-Day Mode",
        initial='closed_all_day',
        help_text="Choose whether the store is fully closed on the off-day or open for special hours"
    )
    weekly_off_open_hour = forms.TypedChoiceField(
        choices=HOUR_CHOICES,
        coerce=int,
        label="Off-Day Open Hour",
        initial=11,
        required=False,
        help_text="Opening hour on weekly off day (IST)"
    )
    weekly_off_open_minute = forms.TypedChoiceField(
        choices=MINUTE_CHOICES,
        coerce=int,
        label="Off-Day Open Minute",
        initial=0,
        required=False,
        help_text="Opening minute on weekly off day"
    )
    weekly_off_close_hour = forms.TypedChoiceField(
        choices=HOUR_CHOICES,
        coerce=int,
        label="Off-Day Close Hour",
        initial=16,
        required=False,
        help_text="Closing hour on weekly off day (IST)"
    )
    weekly_off_close_minute = forms.TypedChoiceField(
        choices=MINUTE_CHOICES,
        coerce=int,
        label="Off-Day Close Minute",
        initial=0,
        required=False,
        help_text="Closing minute on weekly off day"
    )

    class Meta:
        model = StoreInfo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.open_time:
                self.fields['open_hour'].initial = self.instance.open_time.hour
                self.fields['open_minute'].initial = (self.instance.open_time.minute // 5) * 5
            if self.instance.close_time:
                self.fields['close_hour'].initial = self.instance.close_time.hour
                self.fields['close_minute'].initial = (self.instance.close_time.minute // 5) * 5

            if self.instance.weekly_off_open_time and self.instance.weekly_off_close_time:
                self.fields['weekly_off_schedule_type'].initial = 'custom_hours'
                self.fields['weekly_off_open_hour'].initial = self.instance.weekly_off_open_time.hour
                self.fields['weekly_off_open_minute'].initial = (self.instance.weekly_off_open_time.minute // 5) * 5
                self.fields['weekly_off_close_hour'].initial = self.instance.weekly_off_close_time.hour
                self.fields['weekly_off_close_minute'].initial = (self.instance.weekly_off_close_time.minute // 5) * 5
            else:
                self.fields['weekly_off_schedule_type'].initial = 'closed_all_day'

    def save(self, commit=True):
        instance = super().save(commit=False)
        o_h = self.cleaned_data.get('open_hour', 10)
        o_m = self.cleaned_data.get('open_minute', 30)
        c_h = self.cleaned_data.get('close_hour', 20)
        c_m = self.cleaned_data.get('close_minute', 30)

        instance.open_time = time(o_h, o_m)
        instance.close_time = time(c_h, c_m)
        instance.hours_text = instance.get_hours_display()

        schedule_type = self.cleaned_data.get('weekly_off_schedule_type', 'closed_all_day')
        if schedule_type == 'custom_hours':
            wo_oh = self.cleaned_data.get('weekly_off_open_hour', 11)
            wo_om = self.cleaned_data.get('weekly_off_open_minute', 0)
            wo_ch = self.cleaned_data.get('weekly_off_close_hour', 16)
            wo_cm = self.cleaned_data.get('weekly_off_close_minute', 0)
            instance.weekly_off_open_time = time(wo_oh, wo_om)
            instance.weekly_off_close_time = time(wo_ch, wo_cm)
        else:
            instance.weekly_off_open_time = None
            instance.weekly_off_close_time = None

        if commit:
            instance.save()
        return instance


@admin.register(StoreInfo)
class StoreInfoAdmin(admin.ModelAdmin):
    form = StoreInfoAdminForm
    list_display = ('name', 'badge_text', 'get_hours_display', 'phone_number', 'weekly_off_day', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    search_fields = ('name', 'address', 'phone_number')
    fieldsets = (
        ("Store Identity", {
            "fields": ("name", "badge_text", "address", "phone_number", "google_maps_url", "directions_button_text", "is_active")
        }),
        ("Store Regular Operating Hours (IST - Dropdown Selection)", {
            "description": "Select regular store opening and closing hours and minutes using 12h/24h dropdown menus. Values are saved in IST.",
            "fields": (("open_hour", "open_minute"), ("close_hour", "close_minute"), "hours_text", "timezone")
        }),
        ("Weekly Off Day & Operating Schedule (IST)", {
            "description": "Select the day the store has a weekly off/special schedule. You can keep it completely Closed All Day or set custom hours for that day.",
            "fields": (
                "weekly_off_day",
                "weekly_off_schedule_type",
                ("weekly_off_open_hour", "weekly_off_open_minute"),
                ("weekly_off_close_hour", "weekly_off_close_minute"),
            )
        }),
    )

    class Media:
        css = {
            'all': ('admin/css/qr_hub_admin.css',)
        }


@admin.register(SocialChannel)
class SocialChannelAdmin(SortableAdminMixin, admin.ModelAdmin):
    """
    Drag-and-drop sortable social media channel cards.
    Admins can drag rows to reorder them in the list, and changes immediately reflect in the frontend.
    """
    list_display = ('order', 'name', 'handle', 'icon_name', 'button_label', 'click_count', 'is_active', 'is_verified')
    list_display_links = ('name',)
    list_editable = ('is_active', 'is_verified', 'button_label')
    list_filter = ('is_active', 'icon_name', 'is_verified', 'is_featured')
    search_fields = ('name', 'handle', 'url')
    ordering = ('order',)
    fieldsets = (
        ("Card Identity", {
            "fields": ("name", "handle", "url", "icon_name", "button_label", "order")
        }),
        ("Appearance", {
            "fields": ("color", "accent_color")
        }),
        ("Visibility & Badges", {
            "fields": ("is_active", "is_verified", "is_featured")
        }),
    )

    class Media:
        css = {
            'all': ('admin/css/qr_hub_admin.css',)
        }



@admin.register(DynamicQRCode)
class DynamicQRCodeAdmin(admin.ModelAdmin):
    list_display = ('title_display', 'slug', 'target_type_badge', 'encoded_destination', 'encode_mode_badge', 'scan_count', 'is_active', 'qr_preview_link')
    list_editable = ('is_active',)
    list_filter = ('target_type', 'encode_mode', 'is_active', 'include_logo')
    search_fields = ('title', 'slug', 'custom_target_url')
    readonly_fields = ('scan_count', 'last_scanned_at', 'created_at', 'updated_at', 'qr_preview_html')

    class Media:
        css = {
            'all': ('admin/css/qr_hub_admin.css',)
        }

    def title_display(self, obj):
        return format_html('<span style="font-weight: 600; white-space: nowrap;">{}</span>', obj.title)
    title_display.short_description = "Title"

    def target_type_badge(self, obj):
        color_map = {
            'landing_page': ('#10B981', '#ECFDF5'),
            'custom_url': ('#3B82F6', '#EFF6FF'),
            'store_directions': ('#8B5CF6', '#F5F3FF'),
            'whatsapp_direct': ('#059669', '#ECFDF5'),
            'instagram_direct': ('#D97706', '#FFFBEB'),
            'youtube_direct': ('#EF4444', '#FEF2F2'),
        }
        fg, bg = color_map.get(obj.target_type, ('#6B7280', '#F3F4F6'))
        display_label = dict(DynamicQRCode.TARGET_TYPE_CHOICES).get(obj.target_type, obj.target_type)
        return format_html(
            '<span style="display: inline-block; padding: 4px 12px; font-size: 11px; font-weight: 600; '
            'border-radius: 6px; color: {}; background: {}; border: 1px solid {}55; white-space: nowrap;">{}</span>',
            fg, bg, fg, display_label
        )
    target_type_badge.short_description = "Target Type"

    def encode_mode_badge(self, obj):
        if obj.encode_mode == 'direct':
            return mark_safe(
                '<span style="display: inline-block; padding: 4px 12px; font-size: 11px; font-weight: 600; '
                'border-radius: 6px; color: #10B981; background: #ECFDF5; border: 1px solid #10B98155; white-space: nowrap;">'
                'Direct Target</span>'
            )
        else:
            return mark_safe(
                '<span style="display: inline-block; padding: 4px 12px; font-size: 11px; font-weight: 600; '
                'border-radius: 6px; color: #8B5CF6; background: #F5F3FF; border: 1px solid #8B5CF655; white-space: nowrap;">'
                'Dynamic Redirect (/r/)</span>'
            )
    encode_mode_badge.short_description = "Encode Mode"

    def encoded_destination(self, obj):
        url = obj.get_destination_url()
        short = (url[:35] + '...') if len(url) > 35 else url
        return format_html('<a href="{}" target="_blank" style="color: #2563EB; word-break: break-all;">{}</a>', url, short)
    encoded_destination.short_description = "Target Destination"

    def qr_preview_link(self, obj):
        ts = int(obj.updated_at.timestamp()) if obj.updated_at else 0
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px; white-space: nowrap;">'
            '<a href="/api/hub/qr/{}/image/?format=svg&t={}" target="_blank" style="color: #4F46E5; font-weight: 600; text-decoration: underline;">View QR (SVG)</a>'
            '<span style="color: #999;">|</span>'
            '<a href="/api/hub/qr/{}/image/?format=png&size=1000&t={}" download="{}_qr.png" style="color: #059669; font-weight: 600; text-decoration: underline;">Download PNG</a>'
            '</div>',
            obj.slug, ts, obj.slug, ts, obj.slug
        )
    qr_preview_link.short_description = "QR Code Actions"

    def qr_preview_html(self, obj):
        if not obj.pk:
            return "Save first to view QR code preview."
        target_url = obj.get_encoded_data()
        ts = int(obj.updated_at.timestamp()) if obj.updated_at else 0
        return format_html(
            '<div style="background: white; padding: 16px; border-radius: 12px; display: inline-block; border: 1px solid #ddd;">'
            '<img src="/api/hub/qr/{}/image/?format=png&size=300&t={}" width="300" height="300" style="display: block;" />'
            '<p style="margin-top: 8px; font-size: 12px; color: #333; text-align: center;">Scans Open: <a href="{}" target="_blank" style="color: #2563EB; font-weight: 600;"><code>{}</code></a></p>'
            '</div>',
            obj.slug, ts, target_url, target_url
        )
    qr_preview_html.short_description = "Dynamic QR Preview"

    def has_add_permission(self, request):
        # Admin can add only ONE QR code in the system
        return not DynamicQRCode.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevent accidental deletion of the single primary QR code
        return False


@admin.register(QRScanLog)
class QRScanLogAdmin(admin.ModelAdmin):
    list_display = ('qr', 'scanned_at', 'device_type', 'ip_address', 'referrer')
    list_filter = ('device_type', 'scanned_at', 'qr')
    readonly_fields = ('qr', 'scanned_at', 'ip_address', 'user_agent', 'device_type', 'referrer')
    search_fields = ('qr__title', 'qr__slug', 'ip_address', 'user_agent')

    def has_add_permission(self, request):
        return False


@admin.register(ButtonClickLog)
class ButtonClickLogAdmin(admin.ModelAdmin):
    list_display = ('button_type', 'channel_id', 'clicked_at', 'ip_address')
    list_filter = ('button_type', 'clicked_at')
    readonly_fields = ('button_type', 'channel_id', 'clicked_at', 'ip_address', 'user_agent')
    search_fields = ('button_type', 'channel_id', 'ip_address')

    def has_add_permission(self, request):
        return False
