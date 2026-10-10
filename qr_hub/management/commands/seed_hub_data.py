from django.core.management.base import BaseCommand
from qr_hub.views import ensure_initial_seed


class Command(BaseCommand):
    help = 'Seeds initial Store Information, Social Channel Cards, and Dynamic QR Codes for Surya Teja'

    def handle(self, *args, **options):
        self.stdout.write("Seeding initial Surya Teja QR Hub data...")
        ensure_initial_seed()
        self.stdout.write(self.style.SUCCESS("Successfully seeded Surya Teja QR Hub data!"))
