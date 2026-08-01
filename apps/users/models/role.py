from uuid import uuid7

from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class Role(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    name = models.CharField(max_length=50)

    code = models.SlugField(max_length=20, unique=True)

    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name
