from typing import Any
from uuid import uuid7

from django.db import models

from apps.utils.models import (
    SoftDeleteModel,
    TimeStampedModel,
    generate_unique_slug,
)


class Service(TimeStampedModel, SoftDeleteModel):
    class PriceType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        HOURLY = "hourly", "Hourly"

    class ServiceStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CLOSED = "closed", "Closed"

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"
        ON_BREAK = "break", "On Break"
        HOLIDAY = "holiday", "Holiday"

    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
    )

    title = models.CharField(max_length=100)

    slug = models.SlugField(
        max_length=150,
        unique=True,
        blank=True,
        db_index=True,
    )

    description = models.TextField(blank=True)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="services",
        null=True,
        blank=True,
        db_index=True,
    )
    thumbnail = models.ImageField(
        upload_to="services/thumbnails/",
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        "services.ServiceCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        db_index=True,
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
        db_index=True,
    )

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
    )

    price_type = models.CharField(
        max_length=20,
        choices=PriceType.choices,
        default=PriceType.FIXED,
    )
    status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        default=ServiceStatus.DRAFT,
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=10, default="USD")
    skills = models.JSONField(default=list, blank=True)
    radius_km = models.PositiveIntegerField(null=True, blank=True)
    available_from = models.TimeField()

    available_to = models.TimeField()

    def __str__(self) -> str:
        return (
            f"{self.title} unavailable "
            f"from {self.available_from} "
            f"to {self.available_to}"
        )

    def is_currently_available(self) -> bool:
        from django.utils import timezone

        now = timezone.now().time()
        if self.availability_status != self.AvailabilityStatus.AVAILABLE:
            return False
        if self.available_from and self.available_to:
            if self.available_from < self.available_to:
                return self.available_from <= now <= self.available_to

            return now >= self.available_from or now <= self.available_to
        return True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = generate_unique_slug(Service, self.title)

        super().save(*args, **kwargs)
