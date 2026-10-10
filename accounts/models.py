from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random


DEMO_USERNAMES = {"demo_admin", "demo", "demo_user", "demouser", "guest", "preview", "preview_admin"}


def is_demo_user(user) -> bool:
    """Returns True if the user is classified as a demo account."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    username_clean = (user.username or "").strip().lower()
    if username_clean in DEMO_USERNAMES:
        return True
    email_clean = (user.email or "").strip().lower()
    if email_clean and (
        email_clean.startswith("demo") or 
        email_clean.endswith("@demo.com") or 
        email_clean == "demo@example.com" or
        "demouser" in email_clean
    ):
        return True
    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "is_demo", False):
        return True
    return False


def is_master_admin(user) -> bool:
    """Returns True if the user is a superuser / staff and NOT a demo user."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return (user.is_superuser or user.is_staff) and not is_demo_user(user)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mobile = models.CharField(max_length=15, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_demo = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Demo User",
        help_text="Designates whether this account is a demo user for testing and evaluation."
    )

    def __str__(self):
        user_type = "Demo" if self.is_demo else "Real"
        return f"{self.user.email} ({user_type} Profile)"


class TempUser(models.Model):
    """
    Temporary storage for users who have started registration
    but have not yet verified the OTP.
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # already hashed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Temporary User"
        verbose_name_plural = "Temporary Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} (pending OTP)"


class OTP(models.Model):
    PURPOSE_CHOICES = (
        ("register", "Registration"),
        ("change_mobile", "Change Mobile"),
        ("change_name", "Change Name"),
        ("change_email", "Change Email"),
        ("forgot_password", "Forgot Password"),
    )

    email = models.EmailField()
    code = models.CharField(max_length=4)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default="register")
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # OTP valid for only 2 minutes
        return (not self.is_used) and ((timezone.now() - self.created_at).total_seconds() < 120)

    @staticmethod
    def generate_code():
        return f"{random.randint(1000, 9999)}"

    def __str__(self):
        return f"{self.purpose} OTP for {self.email}: {self.code}"





