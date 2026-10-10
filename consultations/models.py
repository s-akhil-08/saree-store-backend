from django.db import models
from django.contrib.auth.models import User


class Consultation(models.Model):
    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("Rejected", "Rejected"),
    )

    # Optional link to authenticated user
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultations",
    )

    # Always store the contact details (works for guests too)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)

    # Appointment details
    date = models.DateField()
    time_slot = models.CharField(max_length=50)          # e.g. "10:00 AM - 11:00 AM"
    topic = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
        db_index=True,
    )

    is_demo = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Demo Booking",
        help_text="Designates whether this consultation was booked by a demo/test account."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Video Consultation"
        verbose_name_plural = "Video Consultations"

    def __str__(self):
        user_info = self.user.email if self.user else "Guest"
        return f"{self.full_name} ({user_info}) – {self.date} {self.time_slot}"

    @property
    def is_authenticated_user(self):
        return self.user is not None

    def save(self, *args, **kwargs):
        from accounts.models import is_demo_user
        if self.user and is_demo_user(self.user):
            self.is_demo = True
        elif self.email and (
            self.email.strip().lower().startswith("demo") or 
            self.email.strip().lower().endswith("@demo.com") or 
            self.email.strip().lower() == "demo@example.com"
        ):
            self.is_demo = True

        status_changed = False
        if self.pk:
            try:
                old_instance = Consultation.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    status_changed = True
            except Consultation.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if status_changed and not self.is_demo:
            self.send_status_update_email()

    def send_status_update_email(self):
        if not self.email:
            return

        status_messages = {
            "Confirmed": "Great news! Your video consultation request has been confirmed for the requested date and time.",
            "Completed": "Thank you for attending your video consultation with us. We hope we were able to assist you!",
            "Cancelled": "Your video consultation request has been cancelled. If you wish to reschedule, please feel free to request a new consultation.",
            "Rejected": "Regrettably, your video consultation request could not be accepted for the selected time slot. Please feel free to request another time slot.",
            "Pending": "Your video consultation status has been updated to Pending. Our team will contact you shortly.",
        }

        status_colors = {
            "Confirmed": "#2e7d32",
            "Completed": "#1565c0",
            "Cancelled": "#c62828",
            "Rejected": "#c62828",
            "Pending": "#f57c00",
        }

        status_str = str(self.status)
        msg = status_messages.get(
            status_str,
            f"Your video consultation status has been updated to {status_str}.",
        )
        color = status_colors.get(status_str, "#f57c00")
        subject = f"Consultation Status: {status_str} – Silk & Loom"

        from accounts.email_utils import send_html_email

        try:
            send_html_email(
                subject=subject,
                template_name="consultation_status_update.html",
                context={
                    "user_name": self.full_name or "Valued Customer",
                    "status": status_str,
                    "status_color": color,
                    "status_message": msg,
                    "date": str(self.date),
                    "time_slot": self.time_slot,
                    "topic": self.topic or "Not specified",
                },
                recipient_list=[self.email],
            )
        except Exception as e:
            print(f"Failed to send consultation status update email: {e}")
