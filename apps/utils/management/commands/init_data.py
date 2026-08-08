from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.jobs.tests.factories import CATEGORIES as JOB_CATEGORIES, JOBS
from apps.services.tests.factories import (
    CATEGORIES as SERVICE_CATEGORIES,
    SERVICES,
)
from apps.users.tests.factories import USERS

# uv run manage.py init_data

SUPERADMIN_DEFAULTS = {
    "username": "superadmin",
    "email": "admin@nepwork.com",
    "full_name": "Site Admin",
    "password": "123",
}


class Command(BaseCommand):
    help = "Initialize development data from the seed_data.json fixtures"

    def handle(self, *args, **kwargs):
        call_command("seed_roles_permissions")

        try:
            call_command("create_superadmin", **SUPERADMIN_DEFAULTS)
        except CommandError as exc:
            self.stdout.write(self.style.WARNING(f"Skipping superadmin: {exc}"))

        call_command(
            "seed",
            users=len(USERS),
            job_categories=len(JOB_CATEGORIES),
            service_categories=len(SERVICE_CATEGORIES),
            jobs=len(JOBS),
            services=len(SERVICES),
        )

        self.stdout.write(self.style.SUCCESS("Development data initialized."))
