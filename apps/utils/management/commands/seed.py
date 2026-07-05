from django.core.management.base import BaseCommand

from apps.jobs.models import Job, JobCategory
from apps.jobs.tests.factories import JobCategoryFactory, JobFactory
from apps.services.models.service_category import ServiceCategory
from apps.services.models.services import Service
from apps.services.tests.factories import ServiceCategoryFactory, ServiceFactory
from apps.skill.models import Skill
from apps.users.models.user import User
from apps.users.tests.factories import UserFactory

# python manage.py seed --services 30


class Command(BaseCommand):
    help = "Seed database"

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=0)
        parser.add_argument("--services", type=int, default=0)
        parser.add_argument("--jobs", type=int, default=0)
        parser.add_argument("--service-categories", type=int, default=0)
        parser.add_argument("--job-categories", type=int, default=0)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        users_count = options["users"]
        services_count = options["services"]
        jobs_count = options["jobs"]
        service_categories_count = options["service_categories"]
        job_categories_count = options["job_categories"]
        reset = options["reset"]

        self.stdout.write(" Seeding started...")

        # RESET
        if reset:
            self.stdout.write(" Clearing data...")
            Service.objects.all().delete()
            Job.objects.all().delete()
            ServiceCategory.objects.all().delete()
            JobCategory.objects.all().delete()
            User.objects.all().delete()
            Skill.objects.all().delete()

        # SERVICE CATEGORIES
        if service_categories_count > 0:
            self.stdout.write(
                f" Creating {service_categories_count} service categories..."
            )
            ServiceCategoryFactory.create_batch(service_categories_count)

        # JOB CATEGORIES
        if job_categories_count > 0:
            self.stdout.write(
                f" Creating {job_categories_count} job categories..."
            )
            JobCategoryFactory.create_batch(job_categories_count)

        # USERS
        if users_count > 0:
            self.stdout.write(f" Creating {users_count} users...")
            UserFactory.create_batch(users_count)

        # SERVICES
        if services_count > 0:
            self.stdout.write(f"🛠 Creating {services_count} services...")
            ServiceFactory.create_batch(services_count)

        # JOBS
        if jobs_count > 0:
            self.stdout.write(f"💼 Creating {jobs_count} jobs...")
            JobFactory.create_batch(jobs_count)

        self.stdout.write(self.style.SUCCESS("Seeding completed"))
