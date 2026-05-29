from uuid import uuid7

from django.db import models

from apps.users.models.user import User
from apps.utils.models import SoftDeleteModel, TimeStampedModel


class ServiceRequest(TimeStampedModel, SoftDeleteModel):
    class ServiceRequestStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In Review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="service_requests"
    )

    service = models.ForeignKey(
        "services.Service",
        on_delete=models.CASCADE,
        related_name="service_requests",
    )

    request_message = models.TextField(blank=True)

    response_message = models.TextField(
        blank=True,
        help_text="Provider response or negotiation message",
    )
    status = models.CharField(
        max_length=20,
        choices=ServiceRequestStatus.choices,
        default=ServiceRequestStatus.OPEN,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    budget = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(
        max_length=10,
        default="USD",
    )
    preferred_date = models.DateField(
        null=True,
        blank=True,
    )

    preferred_time = models.TimeField(
        null=True,
        blank=True,
    )

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
    )

    estimated_duration_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    is_negotiable = models.BooleanField(
        default=True,
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.user} → {self.service} ({self.status})"
