from uuid import uuid7

from django.db import models

from apps.utils.models import TimeStampedModel

from .user import User


class OrganizationProfile(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="organization_profile",
    )

    industry = models.CharField(max_length=50, blank=True)

    logo = models.ImageField(upload_to="org_logos/", blank=True)

    employees_count = models.PositiveIntegerField(blank=True, null=True)

    founded_at = models.DateField(blank=True, null=True)

    address = models.TextField(blank=True)

    tax_id = models.CharField(max_length=50, blank=True)

    is_verified = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"OrganizationProfile({self.user.username})"
