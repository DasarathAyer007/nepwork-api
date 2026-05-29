from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class JobCategory(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional icon name or identifier",
    )

    def __str__(self) -> str:
        return self.name
