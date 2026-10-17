import secrets
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def database_keepalive(request):
    expected_token = getattr(settings, "SUPABASE_KEEPALIVE_TOKEN", "")
    provided_token = request.headers.get(
        "X-Keepalive-Token", ""
    )
    if not expected_token or not secrets.compare_digest(
        provided_token, expected_token
    ):
        return JsonResponse(
            {"error": "Unauthorized"},
            status=403,
        )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations"
            )
            cursor.fetchone()
        return JsonResponse({
            "status": "ok",
            "database": "connected",
        })
    except Exception:
        return JsonResponse(
            {"status": "error", "database": "unavailable"},
            status=503,
        )
