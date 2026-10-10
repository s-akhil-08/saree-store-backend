from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile
from consultations.models import Consultation
from products.models import Product, WishlistItem, ContactLog


class Command(BaseCommand):
    help = "Populates comprehensive demo data (users, consultations, wishlists, contact inquiries) isolated strictly for demo accounts."

    def handle(self, *args, **options):
        # 1. Demo Staff Admin (for Admin Dashboard demo access)
        demo_admin, _ = User.objects.get_or_create(
            username="demo_admin",
            defaults={"email": "demo@example.com", "is_staff": True, "is_active": True}
        )
        demo_admin.is_staff = True
        demo_admin.is_active = True
        if not demo_admin.check_password("DemoAdmin@123"):
            demo_admin.set_password("DemoAdmin@123")
            demo_admin.save()
        else:
            demo_admin.save(update_fields=["is_staff", "is_active"])

        p_admin, _ = Profile.objects.get_or_create(user=demo_admin)
        p_admin.first_name = "Demo"
        p_admin.last_name = "Admin"
        p_admin.mobile = "+919999999999"
        p_admin.is_demo = True
        p_admin.save()
        self.stdout.write(self.style.SUCCESS("[OK] Demo Admin configured: demo_admin / demo@example.com (Password: DemoAdmin@123)"))

        # 2. Demo Customers (for Storefront and User table demo)
        demo_users_data = [
            ("demo_user", "demouser@gmail.com", "Demo", "Customer", "+919999999999"),
            ("demo_priya", "priya.demo@gmail.com", "Priya", "Sharma", "+919999999991"),
            ("demo_ananya", "ananya.demo@gmail.com", "Ananya", "Reddy", "+919999999992"),
        ]

        created_users = {}
        for username, email, first_name, last_name, mobile in demo_users_data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_staff": False, "is_active": True}
            )
            user.email = email
            user.is_staff = False
            user.is_active = True
            if not user.check_password("DemoUser@123"):
                user.set_password("DemoUser@123")
                user.save()
            else:
                user.save(update_fields=["email", "is_staff", "is_active"])

            prof, _ = Profile.objects.get_or_create(user=user)
            prof.first_name = first_name
            prof.last_name = last_name
            prof.mobile = mobile
            prof.is_demo = True
            prof.save()
            created_users[username] = user
            self.stdout.write(self.style.SUCCESS(f"[OK] Demo User configured: {username} ({email})"))

        # 3. Demo Consultations (is_demo=True)
        Consultation.objects.filter(is_demo=True).delete()
        now = timezone.now().date()
        consultations_data = [
            {
                "user": created_users["demo_priya"],
                "full_name": "Priya Sharma",
                "email": "priya.demo@gmail.com",
                "mobile": "+919876543210",
                "date": now + timedelta(days=1),
                "time_slot": "11:00 AM - 11:45 AM",
                "topic": "Bridal Pure Silk Saree Selection & Color Matching",
                "notes": "Looking for traditional red/gold Kanchipuram bridal saree for upcoming wedding.",
                "status": "Pending",
                "is_demo": True,
            },
            {
                "user": created_users["demo_ananya"],
                "full_name": "Ananya Reddy",
                "email": "ananya.demo@gmail.com",
                "mobile": "+919876543211",
                "date": now + timedelta(days=3),
                "time_slot": "03:00 PM - 03:45 PM",
                "topic": "Handloom Gadwal Saree Styling & Blouse Pairing",
                "notes": "Interested in handwoven silk-cotton Gadwal sarees for reception event.",
                "status": "Confirmed",
                "is_demo": True,
            },
            {
                "user": None,
                "full_name": "Meera Iyer (Guest)",
                "email": "meera.guest@demo.com",
                "mobile": "+919876543212",
                "date": now - timedelta(days=2),
                "time_slot": "04:00 PM - 04:45 PM",
                "topic": "Festive Saree Gifting & Packaging Inquiry",
                "notes": "Consultation completed successfully. Recommended 3 Mysore silk sarees.",
                "status": "Completed",
                "is_demo": True,
            },
        ]

        for c_data in consultations_data:
            Consultation.objects.create(**c_data)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(consultations_data)} demo consultations (Pending, Confirmed, Completed)"))

        # 4. Demo Wishlist Items
        sample_products = list(Product.objects.all())
        if sample_products:
            WishlistItem.objects.filter(user__in=created_users.values()).delete()
            created_wishlist_count = 0
            for u in created_users.values():
                for p in sample_products[:4]:
                    WishlistItem.objects.get_or_create(user=u, product=p)
                    created_wishlist_count += 1
            self.stdout.write(self.style.SUCCESS(f"[OK] Created {created_wishlist_count} demo wishlist items across demo accounts"))

        # 5. Demo WhatsApp Contact Inquiries
        ContactLog.objects.filter(is_demo=True).delete()
        contacts_data = [
            {
                "user": created_users["demo_user"],
                "product": sample_products[0] if sample_products else None,
                "guest_name": "Demo Customer",
                "guest_mobile": "+919999999998",
                "is_demo": True,
            },
            {
                "user": created_users["demo_priya"],
                "product": sample_products[1] if len(sample_products) > 1 else None,
                "guest_name": "Priya Sharma",
                "guest_mobile": "+919876543210",
                "is_demo": True,
            },
            {
                "user": created_users["demo_ananya"],
                "product": sample_products[2] if len(sample_products) > 2 else None,
                "guest_name": "Ananya Reddy",
                "guest_mobile": "+919876543211",
                "is_demo": True,
            },
            {
                "user": None,
                "product": sample_products[0] if sample_products else None,
                "guest_name": "Sneha Rao (Guest)",
                "guest_mobile": "+919876543220",
                "is_demo": True,
            },
            {
                "user": None,
                "product": sample_products[1] if len(sample_products) > 1 else None,
                "guest_name": "Meenakshi Sundaram (Guest)",
                "guest_mobile": "+919876543221",
                "is_demo": True,
            },
            {
                "user": None,
                "product": sample_products[2] if len(sample_products) > 2 else None,
                "guest_name": "Divya Patel (Guest)",
                "guest_mobile": "+919876543222",
                "is_demo": True,
            },
            {
                "user": None,
                "product": sample_products[3] if len(sample_products) > 3 else None,
                "guest_name": "Pooja Hegde (Guest)",
                "guest_mobile": "+919876543223",
                "is_demo": True,
            },
        ]
        for ct in contacts_data:
            ContactLog.objects.create(**ct)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(contacts_data)} demo WhatsApp contact inquiry logs"))
        self.stdout.write(self.style.SUCCESS("[SUCCESS] Demo dataset successfully populated and isolated!"))


