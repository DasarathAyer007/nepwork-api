from uuid import uuid7

from django.db import models

from apps.skill.models import Skill
from apps.utils.models import TimeStampedModel

from .user import User


class PersonalProfile(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        NOT_SPECIFIED = "not_specified", "Not Specified"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="personal_profile"
    )

    date_of_birth = models.DateField(blank=True, null=True)

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.NOT_SPECIFIED,
    )

    skills = models.ManyToManyField(Skill, blank=True)

    interests = models.JSONField(default=list, blank=True)
