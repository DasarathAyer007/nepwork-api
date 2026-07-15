from django.core.management import call_command
from django.core.management.base import BaseCommand

# uv run manage.py init_data


class Command(BaseCommand):
    help = "Initialize development data"

    def handle(self, *args, **kwargs):
        call_command(
            "seed",
            users=10,
            job_categories=16,
            service_categories=18,
            jobs=60,
            services=100,
        )

        self.stdout.write(self.style.SUCCESS("Development data initialized."))
