from uuid import uuid7

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.utils.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    class AccountType(models.TextChoices):
        PERSONAL = "personal", "Personal"
        ORGANIZATION = "organization", "Organization"
        ADMIN = "admin", "Admin"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"
        BLOCKED = "blocked", "Blocked"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    full_name = models.CharField(max_length=100, blank=True)

    username = models.CharField(max_length=50, unique=True, db_index=True)

    email = models.EmailField(unique=True, db_index=True)

    password = models.CharField(max_length=255)

    phone_number = models.CharField(max_length=20, blank=True)

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.PERSONAL,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", blank=True, null=True
    )
    cover_photo = models.ImageField(
        upload_to="cover_photos/", blank=True, null=True
    )

    two_factor_enabled = models.BooleanField(default=False)

    last_login_at = models.DateTimeField(null=True, blank=True)

    last_active_at = models.DateTimeField(blank=True, null=True)

    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    failed_login_attempts = models.PositiveIntegerField(default=0)

    is_locked = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.full_name if self.full_name else self.username
