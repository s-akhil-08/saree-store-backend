from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from .models import Consultation
from .serializers import ConsultationCreateSerializer, ConsultationSerializer



class ConsultationCreateView(APIView):
    """
    POST /api/consultations/
    Works for both authenticated and guest users.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConsultationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # If user is logged in, attach the user
        user = request.user if request.user.is_authenticated else None

        consultation = serializer.save(user=user, status="Pending")

        # 1. Notify all staff users (only for real customer requests)
        if not consultation.is_demo:
            self._notify_staff(consultation)

        # 2. Send confirmation email to the customer (if real)
        if not consultation.is_demo:
            self._notify_customer(consultation)

        return Response(
            {
                "message": "Video consultation requested successfully.",
                "consultation": ConsultationSerializer(consultation).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _notify_staff(self, consultation):
        """
        Send consultation details to staff & admin notification email.
        """
        try:
            admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
            staff_emails = []
            if admin_email and isinstance(admin_email, str) and "@" in admin_email:
                staff_emails.append(admin_email)

            db_staff = list(
                User.objects.filter(is_staff=True, is_active=True)
                .exclude(email="")
                .values_list("email", flat=True)
            )
            for e in db_staff:
                if e and isinstance(e, str) and "@" in e and e not in staff_emails:
                    staff_emails.append(e)

            if not staff_emails:
                print("No valid staff emails found. Skipping staff notification.")
                return

            subject = f"New Video Consultation Request – {consultation.full_name}"
            user_type = "Authenticated User" if consultation.user else "Guest User"

            message = (
                f"A new video consultation has been requested.\n\n"
                f"Type          : {user_type}\n"
                f"Name          : {consultation.full_name}\n"
                f"Email         : {consultation.email}\n"
                f"Mobile        : {consultation.mobile}\n"
                f"Date          : {consultation.date}\n"
                f"Time Slot     : {consultation.time_slot}\n"
                f"Topic         : {consultation.topic or '-'}\n"
                f"Notes         : {consultation.notes or '-'}\n"
                f"Status        : {consultation.status}\n\n"
                f"Please log in to the Admin Panel to review and update the status."
            )

            html_content = render_to_string('emails/consultation_admin.html', {
                'user_type': user_type,
                'full_name': consultation.full_name,
                'email': consultation.email,
                'mobile': consultation.mobile,
                'date': consultation.date,
                'time_slot': consultation.time_slot,
                'topic': consultation.topic or '-',
                'notes': consultation.notes or '-',
                'admin_login_url': f"{getattr(settings, 'SITE_URL', 'https://backend-application-q9i2.onrender.com')}/admin/"
            })

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=staff_emails,
                fail_silently=True,
                html_message=html_content,
            )
        except Exception as e:
            print(f"Failed to send staff notification: {e}")

    def _notify_customer(self, consultation):
        """
        Send a confirmation email to the customer who submitted the form.
        """
        try:
            if not consultation.email:
                print("No customer email found. Skipping customer confirmation.")
                return

            subject = "Your Video Consultation Request has been received – Silk & Loom"

            message = (
                f"Dear {consultation.full_name},\n\n"
                f"Thank you for requesting a video consultation with Silk & Loom.\n\n"
                f"Your consultation request has been successfully created with the following details:\n\n"
                f"Date          : {consultation.date}\n"
                f"Time Slot     : {consultation.time_slot}\n"
                f"Topic         : {consultation.topic or 'Not specified'}\n"
                f"Status        : Pending\n\n"
                f"Our team will contact you soon to confirm the appointment.\n\n"
                f"If you have any questions, feel free to reply to this email.\n\n"
                f"Warm regards,\n"
                f"Team Silk & Loom"
            )

            html_content = render_to_string('emails/consultation_user.html', {
                'user_name': consultation.full_name.split()[0] if consultation.full_name else 'Valued Customer',
                'date': consultation.date,
                'time_slot': consultation.time_slot,
                'topic': consultation.topic or 'Not specified',
            })

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[consultation.email],
                fail_silently=True,
                html_message=html_content,
            )
        except Exception as e:
            print(f"Failed to send customer confirmation: {e}")
        except Exception as e:
            print(f"Failed to send customer confirmation: {e}")


class ConsultationListView(APIView):
    """
    GET /api/consultations/list/
    Returns only the consultations of the currently logged-in user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        consultations = Consultation.objects.filter(user=request.user)
        serializer = ConsultationSerializer(consultations, many=True)
        return Response(serializer.data)

