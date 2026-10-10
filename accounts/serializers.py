from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, OTP, TempUser


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        value = value.lower()
        if not value.endswith("@gmail.com"):
            raise serializers.ValidationError("Only Gmail addresses (@gmail.com) are allowed.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if TempUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A registration with this email is already in progress. Please complete OTP verification or try again later."
            )
        return value

    def validate_mobile(self, value):
        val_str = str(value).strip()
        digits = "".join(filter(str.isdigit, val_str))
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) != 10 or digits[0] not in "6789":
            raise serializers.ValidationError("Please enter a valid 10-digit Indian mobile number.")

        formatted = f"+91{digits}"

        if Profile.objects.filter(mobile=formatted).exists() or TempUser.objects.filter(mobile=formatted).exists() or Profile.objects.filter(mobile=digits).exists() or TempUser.objects.filter(mobile=digits).exists():
            raise serializers.ValidationError("This number already exists")
        return formatted

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)
    purpose = serializers.CharField(required=False, default="register")


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    mobile = serializers.CharField(source="profile.mobile", read_only=True)
    first_name = serializers.CharField(source="profile.first_name", read_only=True)
    last_name = serializers.CharField(source="profile.last_name", read_only=True)
    is_demo = serializers.BooleanField(source="profile.is_demo", read_only=True, default=False)

    class Meta:
        model = User
        fields = ["id", "email", "name", "first_name", "last_name", "mobile", "is_demo"]

    def get_name(self, obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.first_name:
            return f"{profile.first_name} {profile.last_name}".strip()
        return obj.username or obj.email.split("@")[0]


# ---------- Profile change requests ----------
class RequestChangeNameSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)


class RequestChangeMobileSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)

    def validate_mobile(self, value):
        val_str = str(value).strip()
        digits = "".join(filter(str.isdigit, val_str))
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]

        if len(digits) != 10 or digits[0] not in "6789":
            raise serializers.ValidationError("Please enter a valid 10-digit Indian mobile number.")

        formatted = f"+91{digits}"

        if Profile.objects.filter(mobile=formatted).exists() or Profile.objects.filter(mobile=digits).exists():
            raise serializers.ValidationError("This number already exists")
        return formatted


class RequestChangeEmailSerializer(serializers.Serializer):
    new_email = serializers.EmailField()

    def validate_new_email(self, value):
        value = value.lower()
        if not value.endswith("@gmail.com"):
            raise serializers.ValidationError("Only Gmail addresses (@gmail.com) are allowed.")
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered. Please try a different email.")
        return value


# ---------- Forgot Password ----------
class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data