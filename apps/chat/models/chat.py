from uuid import uuid7

from django.db import models

from apps.utils.models.soft_delete import SoftDeleteModel
from apps.utils.models.timestamp import TimeStampedModel


class Chat(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, blank=True)
    members = models.ManyToManyField("users.User", related_name="chats")

    def __str__(self):
        return self.name or f"Chat {self.id}"
