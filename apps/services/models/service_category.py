from uuid import uuid7

from django.core.validators import FileExtensionValidator
from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class ServiceCategory(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    name = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    description = models.TextField(blank=True)

    icon = models.FileField(
        upload_to="service_category/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["svg"])],
        help_text="Custom SVG icon uploaded by admin",
    )

    color = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional color code in hex format (e.g., #RRGGBB)",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name
