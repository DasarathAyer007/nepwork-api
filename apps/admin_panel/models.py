from uuid import uuid7

from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class SlidingImage(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    image = models.ImageField(upload_to="sliding_images/")
    caption = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return self.caption or str(self.id)
