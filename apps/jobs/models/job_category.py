from uuid import uuid7

from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class JobCategory(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional icon name or identifier",
    )
    color = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional color code in hex format (e.g., #RRGGBB)",
    )

    def __str__(self) -> str:
        return self.name
