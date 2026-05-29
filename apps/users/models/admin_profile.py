from uuid import uuid7

from django.db import models

from apps.utils.models import TimeStampedModel

from .user import User


class AdminProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="admin_profile"
    )
    role = models.CharField(max_length=20, blank=True)

    ip_address = models.GenericIPAddressField(blank=True, null=True)

    department = models.CharField(max_length=50, blank=True)

    designation = models.CharField(max_length=50, blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_admin_profiles",
    )

    notes = models.TextField(
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.user.username} - {self.role}"
