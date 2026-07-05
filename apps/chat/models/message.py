from uuid import uuid7

from django.db import models

from apps.utils.models.soft_delete import SoftDeleteModel
from apps.utils.models.timestamp import TimeStampedModel

from .chat import Chat


class Message(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    chat = models.ForeignKey(
        Chat, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="messages"
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
