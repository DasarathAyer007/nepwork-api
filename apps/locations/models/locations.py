from uuid import uuid7

from django.contrib.gis.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class Location(TimeStampedModel, SoftDeleteModel):
    class VisibilityLevel(models.IntegerChoices):
        EXACT = 0, "Exact"
        STREET = 1, "Street"
        AREA = 2, "Area"
        CITY = 3, "City"
        STATE = 4, "State"
        COUNTRY = 5, "Country"
        HIDDEN = 6, "Hidden"
        PRIVATE = 7, "Private"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    point = models.PointField(
        geography=True,
        srid=4326,
        spatial_index=True,
    )

    address = models.TextField(blank=True)

    city = models.CharField(max_length=100, blank=True)

    state = models.CharField(max_length=100, blank=True)

    country = models.CharField(max_length=100, blank=True)

    postal_code = models.CharField(max_length=20, blank=True)

    label = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. Home, Office, Client location",
    )

    visibility_level = models.CharField(
        max_length=20, choices=VisibilityLevel.choices
    )

    def __str__(self) -> str:
        return f"{self.city}, {self.country}"
