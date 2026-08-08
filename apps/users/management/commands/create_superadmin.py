import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.users.models import AdminProfile, Role, User

# Examples:
# python manage.py create_superadmin
# python manage.py create_superadmin --username admin
# python manage.py create_superadmin --username admin --email admin@example.com


class Command(BaseCommand):
    help = (
        "Creates the first superadmin account (User + AdminProfile, "
        "role=superadmin, is_superuser/is_staff=True)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Username")
        parser.add_argument("--email", help="Email address")
        parser.add_argument("--full-name", default=None, help="Full name")
        parser.add_argument(
            "--password",
            help="Password (if omitted, you will be prompted securely).",
        )

    def prompt(self, message, required=True):
        """
        Prompt for text input.
        """
        while True:
            value = input(message).strip()
            if value or not required:
                return value
            self.stdout.write(self.style.ERROR("This field is required."))

    def prompt_password(self, user=None):
        """
        Prompt until a valid password is entered.
        """
        while True:
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm password: ")

            if not password:
                self.stdout.write(self.style.ERROR("Password cannot be empty."))
                continue

            if password != confirm:
                self.stdout.write(self.style.ERROR("Passwords do not match.\n"))
                continue

            # try:
            #     validate_password(password, user=user)
            # except ValidationError as exc:
            #     for error in exc.messages:
            #         self.stdout.write(self.style.ERROR(f"- {error}"))
            #     self.stdout.write("")
            #     continue

            return password

    def handle(self, *args, **options):
        self.stdout.write(" Creating superadmin account...")

        username = options.get("username")
        email = options.get("email")
        full_name = options.get("full_name")
        password = options.get("password")

        # Prompt for missing values
        if not username:
            username = self.prompt("Username: ")

        if not email:
            email = self.prompt("Email: ")

        if full_name is None:
            full_name = self.prompt("Full name (optional): ", required=False)

        # Check duplicates
        if User.objects.filter(username=username).exists():
            raise CommandError(
                f"A user with username '{username}' already exists."
            )

        if User.objects.filter(email=email).exists():
            raise CommandError(f"A user with email '{email}' already exists.")

        # Get superadmin role
        try:
            role = Role.objects.get(code="superadmin")
        except Role.DoesNotExist as exc:
            raise CommandError(
                "Role 'superadmin' does not exist. "
                "Run `python manage.py seed_roles_permissions` first."
            ) from exc

        # Create temporary user for password validation
        temp_user = User(
            username=username,
            email=email,
        )

        # Prompt for password if not supplied
        if not password:
            password = self.prompt_password(temp_user)
        else:
            try:
                validate_password(password, user=temp_user)
            except ValidationError as exc:
                raise CommandError("\n".join(exc.messages))

        with transaction.atomic():
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                account_type=User.AccountType.ADMIN,
                is_active=True,
                is_staff=True,
                is_superuser=True,
            )
            user.set_password(password)
            user.save()

            AdminProfile.objects.create(
                user=user,
                role=role,
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("✓ Superadmin created successfully!")
        )
        self.stdout.write(f"Username : {user.username}")
        self.stdout.write(f"Email    : {user.email}")
        self.stdout.write(f"User ID  : {user.id}")
