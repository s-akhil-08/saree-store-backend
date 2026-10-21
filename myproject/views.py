import time
import secrets
import platform
import subprocess
import django
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET


@require_GET
def database_keepalive(request):
    """
    Harmless, read-only endpoint that pings the Supabase database
    to register activity and prevent inactive project auto-pausing.
    """
    expected_token = getattr(settings, "SUPABASE_KEEPALIVE_TOKEN", "")
    provided_token = request.headers.get("X-Keepalive-Token", "")
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


@require_GET
def terminal_status_view(request):
    """
    Renders an immersive full-window, black-only CLI terminal interface
    displaying real-time backend node diagnostics, dynamic API health,
    GitHub developer profile details, and a prominent button to the Django Admin Panel.
    Fully responsive from 320px mobile screens to 4K ultra-wide monitors.
    """
    t0 = time.perf_counter()
    db_status = "ONLINE"
    db_latency_ms = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    except Exception as e:
        db_status = f"DEGRADED ({e.__class__.__name__})"

    # Fetch latest git commit information if available
    last_commit_hash = "998f370"
    last_commit_msg = "perf(admin): optimize queries, add 60s caching, dynamic pagination"
    try:
        commit_out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=1
        ).decode("utf-8").strip()
        if commit_out:
            last_commit_hash = commit_out
        msg_out = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"],
            stderr=subprocess.DEVNULL,
            timeout=1
        ).decode("utf-8").strip()
        if msg_out:
            last_commit_msg = msg_out
    except Exception:
        pass

    is_ssl = request.is_secure() or request.headers.get("x-forwarded-proto") == "https"
    protocol = "HTTPS (Encrypted)" if is_ssl else "HTTP (Standard)"

    context = {
        "django_version": django.get_version(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "server_time_utc": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "db_status": db_status,
        "db_latency_ms": db_latency_ms,
        "host": request.get_host(),
        "protocol": protocol,
        "github_user": "s-akhil-08",
        "github_profile_url": "https://github.com/s-akhil-08",
        "github_repo_url": "https://github.com/s-akhil-08/saree-store-backend",
        "git_branch": "main",
        "last_commit_hash": last_commit_hash,
        "last_commit_msg": last_commit_msg,
    }
    return render(request, "terminal_status.html", context)
