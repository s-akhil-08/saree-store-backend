from django.contrib.auth.models import User
from django.db.models import Q
from products.models import Product, Category, WishlistItem, ContactLog
from consultations.models import Consultation
from accounts.models import is_demo_user, DEMO_USERNAMES


def admin_dashboard_stats(request):
    """
    Context processor to inject dynamic counters and metrics into the Django Admin Dashboard.
    Strictly isolates Demo Data from Real Production Customer Data:
    - Master Admin: Focuses purely on Real Customer activity (with secondary demo counts).
    - Demo Admin: Focuses strictly on Demo Sandbox test activity.
    """
    if not request.path.startswith("/admin"):
        return {}

    user = request.user
    if not user or not user.is_authenticated or not (user.is_staff or user.is_superuser):
        return {}

    is_demo = is_demo_user(user)

    try:
        total_products = Product.objects.count()
        total_categories = Category.objects.count()
        total_new_arrivals = Product.objects.filter(is_new_arrival=True).count()

        if is_demo:
            # Demo Staff Session: Only view demo data counters
            demo_users_count = User.objects.filter(
                Q(profile__is_demo=True) | Q(username__in=DEMO_USERNAMES)
            ).count()
            total_users = demo_users_count
            real_users = 0
            demo_users = demo_users_count

            total_consultations = Consultation.objects.filter(is_demo=True).count()
            pending_consultations = Consultation.objects.filter(is_demo=True, status="Pending").count()
            total_wishlists = WishlistItem.objects.filter(
                Q(user__profile__is_demo=True) | Q(user__username__in=DEMO_USERNAMES)
            ).count()
            total_contacts = ContactLog.objects.filter(is_demo=True).count()
            demo_consultations_count = total_consultations
            demo_wishlists_count = total_wishlists
            demo_contacts_count = total_contacts
        else:
            # Master Admin Session: Main metrics reflect REAL PRODUCTION customer business data!
            real_users = User.objects.filter(
                is_staff=False, is_superuser=False
            ).exclude(profile__is_demo=True).exclude(username__in=DEMO_USERNAMES).count()
            
            demo_users = User.objects.filter(
                Q(profile__is_demo=True) | Q(username__in=DEMO_USERNAMES)
            ).count()
            
            # Primary counters for Master Admin: Real customer data only
            total_users = real_users
            
            total_consultations = Consultation.objects.filter(is_demo=False).count()
            pending_consultations = Consultation.objects.filter(is_demo=False, status="Pending").count()
            demo_consultations_count = Consultation.objects.filter(is_demo=True).count()

            total_wishlists = WishlistItem.objects.exclude(
                Q(user__profile__is_demo=True) | Q(user__username__in=DEMO_USERNAMES)
            ).count()
            demo_wishlists_count = WishlistItem.objects.filter(
                Q(user__profile__is_demo=True) | Q(user__username__in=DEMO_USERNAMES)
            ).count()

            total_contacts = ContactLog.objects.filter(is_demo=False).count()
            demo_contacts_count = ContactLog.objects.filter(is_demo=True).count()

        return {
            "dashboard_stats": {
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
                "is_demo_session": is_demo,
            }
        }
    except Exception as e:
        return {"dashboard_stats_error": str(e)}

