from django.core.management.base import BaseCommand

from apps.services.models.services import Service
from apps.services.tests.factories import ServiceCategoryFactory, ServiceFactory
from apps.skill.models import Skill
from apps.users.models.user import User
from apps.users.tests.factories import UserFactory


class Command(BaseCommand):
    help = "Seed database"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=0)
        parser.add_argument("--services", type=int, default=0)
        parser.add_argument("--categories", type=int, default=0)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        users_count = options["users"]
        services_count = options["services"]
        categories_count = options["categories"]
        reset = options["reset"]

        self.stdout.write(" Seeding started...")

        # RESET
        if reset:
            self.stdout.write(" Clearing data...")
            Service.objects.all().delete()
            User.objects.all().delete()
            Skill.objects.all().delete()

        # CATEGORIES
        if categories_count > 0:
            self.stdout.write(f" Creating {categories_count} categories...")
            ServiceCategoryFactory.create_batch(categories_count)

        # USERS
        if users_count > 0:
            self.stdout.write(f" Creating {users_count} users...")
            UserFactory.create_batch(users_count)

        # SERVICES
        if services_count > 0:
            self.stdout.write(f"🛠 Creating {services_count} services...")
            ServiceFactory.create_batch(services_count)

        self.stdout.write(self.style.SUCCESS("Seeding completed"))
