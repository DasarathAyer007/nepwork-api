from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class ServiceCategory(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    description = models.TextField(blank=True)

    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional icon name or identifier",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
