from uuid import uuid7

from django.db import models

from apps.users.models.user import User
from apps.utils.models import SoftDeleteModel, TimeStampedModel

from .services import Service


class ServiceSaved(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_services"
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="saved_by"
    )

    class Meta:
        unique_together = ("user", "service")

    def __str__(self):
        return f"{self.user} saved {self.service}"
