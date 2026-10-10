from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime
import threading

def _send_email_async(email):
    try:
        email.send(fail_silently=True)
    except Exception as e:
        print(f"Async email delivery failed: {e}")


def send_html_email(subject, template_name, context, recipient_list, sync=True):
    """
    Render an HTML template and send it as an email.
    Defaults to sync=True matching CADverse reference project for instant delivery on Vercel/Serverless.
    """
    if not recipient_list:
        return

    # Always add current year
    context.setdefault("year", datetime.now().year)

    html_content = render_to_string(f"emails/{template_name}", context)

    # Plain-text fallback
    text_content = (
        "This is an HTML email. Please view it in an email client that supports HTML."
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    email.attach_alternative(html_content, "text/html")

    if sync:
        try:
            email.send(fail_silently=False)
        except Exception as e:
            print(f"Sync email delivery failed: {e}")
    else:
        threading.Thread(target=_send_email_async, args=(email,), daemon=True).start()
