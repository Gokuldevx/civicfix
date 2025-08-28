from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = "Create a superuser if none exists (using env vars)."

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("SUPERUSER_USERNAME")
        email = os.environ.get("SUPERUSER_EMAIL")
        password = os.environ.get("SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write(self.style.WARNING("SUPERUSER_* env vars not set. Skipping."))
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
        else:
            self.stdout.write(self.style.NOTICE(f"Superuser '{username}' already exists."))
      
