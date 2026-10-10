from django.urls import path
from .views import (
    RegisterView,
    VerifyOTPView,
    LoginView,
    MeView,
    RequestChangeNameView,
    RequestChangeMobileView,
    RequestChangeEmailView,
    ConfirmChangeView,
    ForgotPasswordRequestView,
    VerifyForgotPasswordOTPView,
    ForgotPasswordResetView,
    ResendOTPView,
    LogoutView,
)

urlpatterns = [
    # Auth
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-otp/", VerifyOTPView.as_view(), name="auth-verify-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="auth-resend-otp"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),

    # Profile changes (require login + OTP)
    path("change-name/", RequestChangeNameView.as_view(), name="change-name"),
    path("change-mobile/", RequestChangeMobileView.as_view(), name="change-mobile"),
    path("change-email/", RequestChangeEmailView.as_view(), name="change-email"),
    path("confirm-change/", ConfirmChangeView.as_view(), name="confirm-change"),

    # Forgot Password
    path("forgot-password/", ForgotPasswordRequestView.as_view(), name="forgot-password"),
    path("verify-forgot-otp/", VerifyForgotPasswordOTPView.as_view(), name="verify-forgot-otp"),
    path("reset-password/", ForgotPasswordResetView.as_view(), name="reset-password"),
]