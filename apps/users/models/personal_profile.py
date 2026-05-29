from uuid import uuid7

from django.db import models

from apps.utils.models import TimeStampedModel

from .user import User


class PersonalProfile(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        NOT_SPECIFIED = "not_specified", "Not Specified"

    class ProfileVisibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        LIMITED = "limited", "Limited"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="personal_profile"
    )
    bio = models.TextField(blank=True)

    date_of_birth = models.DateField(blank=True, null=True)

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.NOT_SPECIFIED,
    )

    skills = models.JSONField(default=list, blank=True)

    interests = models.JSONField(default=list, blank=True)

    profile_visibility = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
    )

    social_links = models.JSONField(default=dict, blank=True)
