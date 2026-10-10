from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.conf import settings
from datetime import datetime

from accounts.email_utils import send_html_email
from .models import Profile, OTP, TempUser
from .serializers import (
    RegisterSerializer,
    VerifyOTPSerializer,
    LoginSerializer,
    UserSerializer,
    RequestChangeNameSerializer,
    RequestChangeMobileSerializer,
    RequestChangeEmailSerializer,
    ForgotPasswordRequestSerializer,
    ForgotPasswordResetSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def set_jwt_cookies(response: Response, tokens: dict) -> Response:
    is_secure = not settings.DEBUG
    samesite_val = "None" if is_secure else "Lax"

    # 1 day for access token
    response.set_cookie(
        key="access_token",
        value=tokens["access"],
        max_age=24 * 60 * 60,
        httponly=True,
        secure=is_secure,
        samesite=samesite_val,
        path="/",
    )
    # 7 days for refresh token
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh"],
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=is_secure,
        samesite=samesite_val,
        path="/",
    )
    return response


def clear_jwt_cookies(response: Response) -> Response:
    is_secure = not settings.DEBUG
    samesite_val = "None" if is_secure else "Lax"
    response.delete_cookie("access_token", path="/", samesite=samesite_val)
    response.delete_cookie("refresh_token", path="/", samesite=samesite_val)
    return response


def send_otp_email(email: str, code: str, purpose: str = "verification"):
    """
    Sends the correct HTML OTP email based on purpose.
    """
    if purpose in ["registration", "register"]:
        template = "account_creation_otp.html"
        subject = "Your OTP for Account Verification – Silk & Loom"
    elif purpose in ["password reset", "forgot_password"]:
        template = "password_reset_otp.html"
        subject = "Password Reset OTP – Silk & Loom"
    elif purpose in ["change mobile", "change_mobile", "change email", "change_email", "profile_update"]:
        template = "profile_update_otp.html"
        subject = "Verify Profile Update – Silk & Loom"
    else:
        template = "profile_update_otp.html"
        subject = "Verify Profile Update – Silk & Loom"

    send_html_email(
        subject=subject,
        template_name=template,
        context={
            "otp": code,
            "otp_expiry_minutes": 2,
        },
        recipient_list=[email],
    )


from myproject.throttling import AuthIPThrottle, AuthAccountThrottle

# ------------------------------------------------------------------
# Register
# ------------------------------------------------------------------
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Store in temporary table (password is hashed)
        TempUser.objects.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            mobile=data["mobile"],
            email=data["email"],
            password=make_password(data["password"]),
        )

        # Generate & send OTP
        code = OTP.generate_code()
        OTP.objects.create(email=data["email"], code=code, purpose="register")
        send_otp_email(data["email"], code, "registration")

        return Response(
            {
                "message": "OTP sent to your email. Please verify within 2 minutes.",
                "email": data["email"],
            },
            status=status.HTTP_201_CREATED,
        )


# ------------------------------------------------------------------
# Verify OTP (Account Creation)
# ------------------------------------------------------------------
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        otp_code = serializer.validated_data["otp"]

        try:
            otp_obj = OTP.objects.filter(
                email=email, purpose="register", is_used=False
            ).latest("created_at")
        except OTP.DoesNotExist:
            return Response(
                {"error": "No OTP found. Please register again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_obj.is_valid():
            return Response(
                {"error": "OTP has expired (valid only 2 minutes). Please register again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.code != otp_code:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark OTP used
        otp_obj.is_used = True
        otp_obj.save()

        # Move from TempUser → real User
        try:
            temp = TempUser.objects.get(email=email)
        except TempUser.DoesNotExist:
            return Response(
                {"error": "Registration data not found. Please register again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            existing_user.is_active = True
            existing_user.password = temp.password
            existing_user.save()
            user = existing_user
        else:
            user = User.objects.create(
                username=temp.email,
                email=temp.email,
                password=temp.password,  # already hashed
                is_active=True,
            )

        Profile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": temp.first_name,
                "last_name": temp.last_name,
                "mobile": temp.mobile,
            },
        )

        # Clean up temporary record
        temp.delete()

        # ---------- SEND EMAILS ----------
        # 1. Welcome email to the user
        try:
            send_html_email(
                subject="Welcome to Silk & Loom",
                template_name="welcome.html",
                context={
                    "user_name": f"{temp.first_name} {temp.last_name}".strip(),
                    "shop_url": settings.FRONTEND_URL,
                },
                recipient_list=[user.email],
            )
        except Exception as e:
            print(f"Failed to send welcome email to {user.email}: {e}")

        # 2. Notification to all staff
        admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
        staff_emails = [admin_email] if admin_email and isinstance(admin_email, str) and "@" in admin_email else []
        db_staff = list(
            User.objects.filter(is_staff=True, is_active=True)
            .exclude(email="")
            .values_list("email", flat=True)
        )
        for e in db_staff:
            if e and e not in staff_emails:
                staff_emails.append(e)

        if staff_emails:
            try:
                send_html_email(
                    subject=f"New User Registered – {temp.first_name} {temp.last_name}",
                    template_name="new_user_admin.html",
                    context={
                        "user_name": f"{temp.first_name} {temp.last_name}".strip(),
                        "user_email": user.email,
                        "user_mobile": temp.mobile,
                        "registered_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                        "admin_login_url": settings.ADMIN_LOGIN_URL,
                    },
                    recipient_list=staff_emails,
                )
            except Exception as e:
                print(f"Failed to send admin notification email: {e}")
        # ---------- END EMAILS ----------

        tokens = get_tokens_for_user(user)
        response = Response({
            "message": "Email verified successfully.",
            "user": UserSerializer(user).data,
            "tokens": tokens,
        })
        return set_jwt_cookies(response, tokens)


# ------------------------------------------------------------------
# Login
# ------------------------------------------------------------------
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email_or_username = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]

        user = User.objects.filter(
            models.Q(email__iexact=email_or_username) | models.Q(username__iexact=email_or_username)
        ).first()
        if not user:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"error": "Please verify your email first."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(username=user.username, password=password)
        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = get_tokens_for_user(user)
        response = Response({
            "message": "Login successful.",
            "user": UserSerializer(user).data,
            "tokens": tokens,
        })
        return set_jwt_cookies(response, tokens)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ------------------------------------------------------------------
# Change Name / Mobile / Email (OTP protected)
# ------------------------------------------------------------------
class RequestChangeNameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RequestChangeNameSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        request.user.first_name = serializer.validated_data.get("first_name", request.user.first_name)
        request.user.last_name = serializer.validated_data.get("last_name", request.user.last_name)
        request.user.save()

        if hasattr(request.user, "profile"):
            request.user.profile.first_name = request.user.first_name
            request.user.profile.last_name = request.user.last_name
            request.user.profile.save()

        return Response({"message": "Name updated successfully."})


class RequestChangeMobileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RequestChangeMobileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = OTP.generate_code()
        OTP.objects.create(
            email=request.user.email,
            code=code,
            purpose="change_mobile",
            extra_data={"mobile": serializer.validated_data["mobile"]},
        )
        send_otp_email(request.user.email, code, "change mobile")
        return Response({"message": "OTP sent to your registered email. Valid for 2 minutes."})


class RequestChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RequestChangeEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_email = serializer.validated_data["new_email"]
        code = OTP.generate_code()
        OTP.objects.create(
            email=new_email,  # OTP goes to the NEW email
            code=code,
            purpose="change_email",
            extra_data={"new_email": new_email},
        )
        send_otp_email(new_email, code, "change email")
        return Response({
            "message": "OTP sent to the new email address. Valid for 2 minutes.",
            "new_email": new_email,
        })


class ConfirmChangeView(APIView):
    """
    Common endpoint to confirm any change (name / mobile / email) with OTP.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        purpose = serializer.validated_data.get("purpose")
        otp_code = serializer.validated_data["otp"]
        email = serializer.validated_data["email"].lower()

        try:
            otp_obj = OTP.objects.filter(
                email=email, purpose=purpose, is_used=False
            ).latest("created_at")
        except OTP.DoesNotExist:
            return Response({"error": "No OTP found."}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_obj.is_valid():
            return Response(
                {"error": "OTP has expired (valid only 2 minutes)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.code != otp_code:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save()

        user = request.user
        profile = user.profile
        extra = otp_obj.extra_data

        if purpose == "change_name":
            profile.first_name = extra.get("first_name", profile.first_name)
            profile.last_name = extra.get("last_name", profile.last_name)
            profile.save()
            message = "Name updated successfully."

            send_html_email(
                subject="Your Name Was Updated – Silk & Loom",
                template_name="name_changed.html",
                context={
                    "new_name": f"{profile.first_name} {profile.last_name}".strip(),
                },
                recipient_list=[user.email],
            )

        elif purpose == "change_mobile":
            new_mobile = extra.get("mobile", profile.mobile)
            if Profile.objects.filter(mobile=new_mobile).exclude(user_id=user.id).exists():
                return Response(
                    {"error": "This number already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            profile.mobile = new_mobile
            profile.save()
            message = "Mobile number updated successfully."

            send_html_email(
                subject="Your Mobile Number Was Updated – Silk & Loom",
                template_name="mobile_changed.html",
                context={
                    "user_name": f"{profile.first_name} {profile.last_name}".strip(),
                    "new_mobile": profile.mobile,
                },
                recipient_list=[user.email],
            )

        elif purpose == "change_email":
            new_email = extra.get("new_email")
            if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                return Response(
                    {"error": "This email is already registered."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email = new_email
            user.username = new_email
            user.save()
            message = "Email updated successfully."

            send_html_email(
                subject="Your Email Address Was Updated – Silk & Loom",
                template_name="email_changed.html",
                context={
                    "user_name": f"{profile.first_name} {profile.last_name}".strip(),
                    "new_email": new_email,
                },
                recipient_list=[new_email],
            )

        else:
            return Response({"error": "Invalid purpose."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "user": UserSerializer(user).data,
        })


# ------------------------------------------------------------------
# Forgot Password
# ------------------------------------------------------------------
class VerifyForgotPasswordOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        otp_code = serializer.validated_data["otp"]

        try:
            otp_obj = OTP.objects.filter(
                email=email, purpose="forgot_password", is_used=False
            ).latest("created_at")
        except OTP.DoesNotExist:
            return Response(
                {"error": "No OTP found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_obj.is_valid():
            return Response(
                {"error": "OTP has expired (valid only 2 minutes)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.code != otp_code:
            return Response(
                {"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Do NOT mark as used yet! They still need to reset the password.
        return Response(
            {"message": "OTP verified successfully."}, status=status.HTTP_200_OK
        )

class VerifyForgotPasswordOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        otp_code = serializer.validated_data["otp"]

        try:
            otp_obj = OTP.objects.filter(
                email=email, purpose="forgot_password", is_used=False
            ).latest("created_at")
        except OTP.DoesNotExist:
            return Response(
                {"error": "No OTP found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_obj.is_valid():
            return Response(
                {"error": "OTP has expired (valid only 2 minutes)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.code != otp_code:
            return Response(
                {"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Do NOT mark as used yet! They still need to reset the password.
        return Response(
            {"message": "OTP verified successfully."}, status=status.HTTP_200_OK
        )

class ForgotPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()

        if not User.objects.filter(email__iexact=email).exists():
            return Response(
                {"error": "No account exists with this email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = OTP.generate_code()
        OTP.objects.create(email=email, code=code, purpose="forgot_password")
        send_otp_email(email, code, "password reset")

        return Response({"message": "OTP sent to your email. Valid for 2 minutes."})


class ForgotPasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"].lower()
        otp_code = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        try:
            otp_obj = OTP.objects.filter(
                email=email, purpose="forgot_password", is_used=False
            ).latest("created_at")
        except OTP.DoesNotExist:
            return Response({"error": "No OTP found."}, status=status.HTTP_400_BAD_REQUEST)

        if not otp_obj.is_valid():
            return Response(
                {"error": "OTP has expired (valid only 2 minutes)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.code != otp_code:
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp_obj.is_used = True
        otp_obj.save()

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Send success email
        send_html_email(
            subject="Your Password Has Been Successfully Reset",
            template_name="password_reset_success.html",
            context={
                "user_name": user.get_full_name() or user.username,
                "login_url": f"{settings.FRONTEND_URL}/login",
            },
            recipient_list=[user.email],
        )

        return Response({"message": "Password reset successfully. You can now login."})
class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthIPThrottle, AuthAccountThrottle]

    def post(self, request):
        email = request.data.get('email')
        purpose = request.data.get('purpose', 'register')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        email = email.lower()
        code = OTP.generate_code()
        OTP.objects.create(email=email, code=code, purpose=purpose)
        
        context_str = 'password reset' if purpose == 'forgot_password' else 'registration'
        send_otp_email(email, code, context_str)
        
        return Response({'message': 'OTP resent successfully.'})

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token") or request.data.get("refresh")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception:
                    pass
        except Exception:
            pass

        response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        return clear_jwt_cookies(response)
