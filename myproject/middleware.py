from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse


class ReadOnlyAdminMiddleware:
    """
    Blocks state-modifying requests (POST, PUT, PATCH, DELETE) in Django Admin
    ONLY for demo accounts (e.g. demo_admin, demo, guest) when DEMO_MODE is enabled.
    
    Exemptions:
    - Master / Real Admins (e.g. master_ak, master_ak_11, or any non-demo username)
    - Authentication endpoints (/admin/login/, /admin/logout/)
    """
    DEMO_USERNAMES = {"demo_admin", "demo", "demo_user", "guest", "preview", "preview_admin"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "DEMO_MODE", False):
            # Check if request is targeting the Django Admin panel
            if request.path.startswith("/admin/") and request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                # 1. Allow login and logout for everyone
                is_auth_route = request.path.rstrip("/").endswith("/login") or request.path.rstrip("/").endswith("/logout")
                if is_auth_route:
                    return self.get_response(request)

                # 2. Check if the user is a Demo User
                from accounts.models import is_demo_user
                if request.user.is_authenticated:
                    if not is_demo_user(request.user):
                        return self.get_response(request)

                # 3. Block write access ONLY for demo accounts
                messages.warning(
                    request,
                    "🔒 DEMO MODE: Database modifications (create, update, delete) are disabled for demo accounts."
                )
                referer = request.META.get("HTTP_REFERER")
                if referer:
                    return HttpResponseRedirect(referer)
                return HttpResponseRedirect(reverse("admin:index"))

        return self.get_response(request)
