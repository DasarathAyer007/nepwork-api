from uuid import uuid7

from django.core.validators import FileExtensionValidator
from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class JobCategory(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    icon = models.FileField(
        upload_to="job_category/",
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

    def __str__(self) -> str:
        return self.name
