from uuid import uuid7

from django.db import models

from apps.users.models import User

from .constants import ActivityType, ObjectType


class UserActivity(models.Model):
    """
    Generic event log. No ForeignKey to a specific model, so this can
    track any entity (via object_type + object_id) without a migration.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    activity_type = models.CharField(
        max_length=20, choices=ActivityType.CHOICES
    )

    # object_type + object_id form a "soft" generic reference.
    object_type = models.CharField(
        max_length=30, choices=ObjectType.CHOICES, blank=True
    )
    object_id = models.CharField(max_length=64, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["user", "object_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        target = (
            f"{self.object_type}:{self.object_id}"
            if self.object_type
            else "N/A"
        )
        return f"{self.user} {self.activity_type} {target}"
