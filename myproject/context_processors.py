import logging
from django.core.cache import cache
from django.db.models import Count, Q
from django.contrib.auth.models import User
from products.models import Product, Category, WishlistItem, ContactLog
from consultations.models import Consultation
from accounts.models import is_demo_user, DEMO_USERNAMES

logger = logging.getLogger(__name__)

CACHE_TTL_ADMIN_STATS = 60  # Cache for 60 seconds


def admin_dashboard_stats(request):
    """
    Context processor to inject dynamic counters and real-time database metrics
    into the Django Admin Dashboard.

    Performance optimizations:
    1. Scope check: Only run when rendering the root admin dashboard ('/admin' or '/admin/').
       Changelists, changeforms, popups, and other pages immediately return {} to avoid
       30-40 redundant sequential queries over WAN.
    2. Request-level memoization: Guarantees DB is never hit more than once per HTTP request,
       even when multiple subtemplates are rendered.
    3. Global caching: Results are cached in LocMemCache/Redis for 60 seconds, turning
       repeat visits into 0 DB queries.
    4. Aggregated counts: Consolidates separate queries into single aggregate queries where possible.
    """
    path = request.path.rstrip("/")
    if path != "/admin":
        return {}

    # Check request-level memoization first
    if hasattr(request, "_cached_admin_dashboard_stats"):
        return request._cached_admin_dashboard_stats

    user = request.user
    if not user or not user.is_authenticated or not (user.is_staff or user.is_superuser):
        empty_res = {}
        request._cached_admin_dashboard_stats = empty_res
        return empty_res

    is_demo = is_demo_user(user)
    cache_key = f"admin_dashboard_stats_data_v2_{'demo' if is_demo else 'master'}"

    # Check global cache (TTL: 60s)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        res = {"dashboard_stats": cached_data}
        request._cached_admin_dashboard_stats = res
        return res

    try:
        # Aggregated product counts (1 query instead of 2)
        prod_agg = Product.objects.aggregate(
            total=Count("id"),
            new_arrivals=Count("id", filter=Q(is_new_arrival=True)),
        )
        total_products = prod_agg["total"] or 0
        total_new_arrivals = prod_agg["new_arrivals"] or 0
        total_categories = Category.objects.count()

        try:
            from qr_hub.models import DynamicQRCode, QRScanLog
            total_qr_codes = DynamicQRCode.objects.count()
            total_qr_scans = QRScanLog.objects.count()
        except Exception:
            total_qr_codes = 0
            total_qr_scans = 0

        if is_demo:
            # Demo Staff Session
            demo_users_count = User.objects.filter(
                Q(profile__is_demo=True) | Q(username__in=DEMO_USERNAMES)
            ).count()
            total_users = demo_users_count
            real_users = 0
            demo_users = demo_users_count

            cons_agg = Consultation.objects.filter(is_demo=True).aggregate(
                total=Count("id"),
                pending=Count("id", filter=Q(status="Pending")),
            )
            total_consultations = cons_agg["total"] or 0
            pending_consultations = cons_agg["pending"] or 0

            total_wishlists = WishlistItem.objects.filter(
                Q(user__profile__is_demo=True) | Q(user__username__in=DEMO_USERNAMES)
            ).count()
            total_contacts = ContactLog.objects.filter(is_demo=True).count()
            demo_consultations_count = total_consultations
            demo_wishlists_count = total_wishlists
            demo_contacts_count = total_contacts
        else:
            # Master Admin Session
            real_users = User.objects.filter(
                is_staff=False, is_superuser=False
            ).exclude(profile__is_demo=True).exclude(username__in=DEMO_USERNAMES).count()

            demo_users = User.objects.filter(
                Q(profile__is_demo=True) | Q(username__in=DEMO_USERNAMES)
            ).count()

            total_users = real_users

            cons_agg = Consultation.objects.filter(is_demo=False).aggregate(
                total=Count("id"),
                pending=Count("id", filter=Q(status="Pending")),
            )
            total_consultations = cons_agg["total"] or 0
            pending_consultations = cons_agg["pending"] or 0
            demo_consultations_count = Consultation.objects.filter(is_demo=True).count()

            total_wishlists = WishlistItem.objects.exclude(
                Q(user__profile__is_demo=True) | Q(user__username__in=DEMO_USERNAMES)
            ).count()
            demo_wishlists_count = WishlistItem.objects.filter(
                Q(user__profile__is_demo=True) | Q(user__username__in=DEMO_USERNAMES)
            ).count()

            total_contacts = ContactLog.objects.filter(is_demo=False).count()
            demo_contacts_count = ContactLog.objects.filter(is_demo=True).count()

        stats = {
            "total_users": total_users,
            "real_users": real_users,
            "demo_users": demo_users,
            "total_products": total_products,
            "total_categories": total_categories,
            "total_new_arrivals": total_new_arrivals,
            "total_consultations": total_consultations,
            "pending_consultations": pending_consultations,
            "total_wishlists": total_wishlists,
            "total_contacts": total_contacts,
            "demo_consultations_count": demo_consultations_count,
            "demo_wishlists_count": demo_wishlists_count,
            "demo_contacts_count": demo_contacts_count,
            "total_qr_codes": total_qr_codes,
            "total_qr_scans": total_qr_scans,
            "is_demo_session": is_demo,
        }

        # Cache in memory for 60 seconds
        cache.set(cache_key, stats, CACHE_TTL_ADMIN_STATS)

        res = {"dashboard_stats": stats}
        request._cached_admin_dashboard_stats = res
        return res

    except Exception as e:
        logger.warning("Error generating admin dashboard stats: %s", e)
        res = {"dashboard_stats_error": str(e)}
        request._cached_admin_dashboard_stats = res
        return res
