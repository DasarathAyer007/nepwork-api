from django.db import models

from apps.utils.models.soft_delete import SoftDeleteModel
from apps.utils.models.timestamp import TimeStampedModel


class Notification(SoftDeleteModel, TimeStampedModel):
    class NotificationType(models.TextChoices):
        JOB_APPLICATION_SUBMITTED = (
            "job_application_submitted",
            "Job Application Submitted",
        )
        SERVICE_REQUEST_SUBMITTED = (
            "service_request_submitted",
            "Service Request Submitted",
        )
        JOB_APPLICATION_STATUS_CHANGED = (
            "job_application_status_changed",
            "Job Application Status Changed",
        )
        SERVICE_REQUEST_STATUS_CHANGED = (
            "service_request_status_changed",
            "Service Request Status Changed",
        )

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

    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default="",
        blank=True,
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    # Generic pointer to the resource this notification is about, e.g.
    # entity_type="job_application", entity_id=<application uuid>. The
    # frontend resolves this (plus `data`) into a route — the backend never
    # hands out a URL.
    entity_type = models.CharField(max_length=50, blank=True, default="")

    entity_id = models.CharField(max_length=64, blank=True, default="")

    data = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.recipient} - {self.title}"
