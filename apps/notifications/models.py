from django.db import models

from apps.utils.models.soft_delete import SoftDeleteModel
from apps.utils.models.timestamp import TimeStampedModel


class Notification(SoftDeleteModel, TimeStampedModel):
    recipient = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="notifications"
    )

    sender = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_notifications",
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    action_url = models.CharField(
        max_length=255,
        blank=True,
    )

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} - {self.title}"
