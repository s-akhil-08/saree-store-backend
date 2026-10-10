from rest_framework import serializers
from .models import Consultation


class ConsultationCreateSerializer(serializers.ModelSerializer):
    # Accept the exact keys the frontend currently uses
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    mobile = serializers.CharField(max_length=15)
    date = serializers.DateField()                    # "2026-09-18"
    time_slot = serializers.CharField(max_length=50)  # "10:00 AM - 11:00 AM"
    topic = serializers.CharField(max_length=255, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Consultation
        fields = [
            "full_name",
            "email",
            "mobile",
            "date",
            "time_slot",
            "topic",
            "notes",
        ]

    def validate_mobile(self, value):
        val_str = str(value).strip()
        digits = "".join(filter(str.isdigit, val_str))
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) != 10 or digits[0] not in "6789":
            raise serializers.ValidationError("Please enter a valid 10-digit Indian mobile number.")
        return f"+91{digits}"

class ConsultationSerializer(serializers.ModelSerializer):
    """Used for listing (My Account)"""
    class Meta:
        model = Consultation
        fields = [
            "id",
            "full_name",
            "email",
            "mobile",
            "date",
            "time_slot",
            "topic",
            "notes",
            "status",
            "created_at",
        ]