from rest_framework import serializers
from .models import StoreInfo, SocialChannel, DynamicQRCode, QRScanLog, ButtonClickLog


class StoreInfoSerializer(serializers.ModelSerializer):
    hours_text = serializers.SerializerMethodField()
    weekly_off_hours_text = serializers.SerializerMethodField()

    class Meta:
        model = StoreInfo
        fields = [
            'id',
            'name',
            'badge_text',
            'hours_text',
            'open_time',
            'close_time',
            'timezone',
            'weekly_off_day',
            'weekly_off_open_time',
            'weekly_off_close_time',
            'weekly_off_hours_text',
            'address',
            'phone_number',
            'google_maps_url',
            'directions_button_text',
            'is_active',
            'updated_at',
        ]

    def get_hours_text(self, obj):
        return obj.get_hours_display()

    def get_weekly_off_hours_text(self, obj):
        return obj.get_weekly_off_hours_display()


class SocialChannelSerializer(serializers.ModelSerializer):
    # Field aliases to match frontend mockSocialHandles structure exactly
    id = serializers.CharField(source='channel_id')
    accentColor = serializers.CharField(source='accent_color')
    iconName = serializers.CharField(source='icon_name')
    buttonLabel = serializers.CharField(source='button_label')
    isVerified = serializers.BooleanField(source='is_verified')
    isFeatured = serializers.BooleanField(source='is_featured')

    class Meta:
        model = SocialChannel
        fields = [
            'id',
            'name',
            'handle',
            'url',
            'iconName',
            'color',
            'accentColor',
            'buttonLabel',
            'isVerified',
            'isFeatured',
            'order',
            'is_active',
            'click_count',
        ]


class DynamicQRCodeSerializer(serializers.ModelSerializer):
    destination_url = serializers.SerializerMethodField()
    dynamic_redirect_url = serializers.SerializerMethodField()

    class Meta:
        model = DynamicQRCode
        fields = [
            'id',
            'slug',
            'title',
            'target_type',
            'custom_target_url',
            'destination_url',
            'dynamic_redirect_url',
            'fg_color',
            'bg_color',
            'include_logo',
            'scan_count',
            'last_scanned_at',
            'is_active',
            'created_at',
            'updated_at',
        ]

    def get_destination_url(self, obj):
        return obj.get_destination_url()

    def get_dynamic_redirect_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f"/r/{obj.slug}/")
        return f"/r/{obj.slug}/"


class HubLandingDataSerializer(serializers.Serializer):
    """Full payload for initializing the Surya Teja Hub landing page."""
    store = StoreInfoSerializer()
    channels = SocialChannelSerializer(many=True)
    active_qr = DynamicQRCodeSerializer(allow_null=True)
    profile = serializers.DictField()


class ButtonClickTrackSerializer(serializers.Serializer):
    button_type = serializers.ChoiceField(choices=ButtonClickLog.BUTTON_TYPE_CHOICES)
    channel_id = serializers.CharField(required=False, allow_blank=True, default="")
