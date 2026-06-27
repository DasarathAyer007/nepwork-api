from typing import Any
from uuid import uuid7

from django.db import models

from apps.skill.models import Skill
from apps.utils.models import (
    SoftDeleteModel,
    TimeStampedModel,
    generate_unique_slug,
)


class Job(TimeStampedModel, SoftDeleteModel):
    class JobStatus(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        DRAFT = "draft", "Draft"
        PAUSED = "paused", "Paused"

    class ExperienceLevel(models.TextChoices):
        ENTRY = "entry", "Entry Level"
        MID = "mid", "Mid Level"
        SENIOR = "senior", "Senior Level"
        LEAD = "lead", "Lead"

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        CONTRACT = "contract", "Contract"
        INTERNSHIP = "internship", "Internship"
        FREELANCE = "freelance", "Freelance"

    class WorkMode(models.TextChoices):
        ONSITE = "onsite", "Onsite"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    title = models.CharField(max_length=100)

    slug = models.SlugField(
        max_length=150, unique=True, blank=True, db_index=True
    )

    description = models.TextField()

    thumbnail = models.ImageField(
        upload_to="job_thumbnails/", null=True, blank=True
    )

    posted_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_jobs",
    )

    organization = models.ForeignKey(
        "users.OrganizationProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )

    job_type = models.CharField(
        max_length=15,
        choices=JobType.choices,
        default=JobType.FULL_TIME,
        db_index=True,
    )

    work_mode = models.CharField(
        max_length=15, choices=WorkMode.choices, default=WorkMode.ONSITE
    )

    status = models.CharField(
        max_length=15,
        choices=JobStatus.choices,
        default=JobStatus.DRAFT,
    )

    category = models.ForeignKey(
        "JobCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
        db_index=True,
    )

    skills_required = models.ManyToManyField(Skill, blank=True)

    requirements = models.JSONField(default=list, blank=True)

    experience_level = models.CharField(
        max_length=15,
        choices=ExperienceLevel.choices,
        default=ExperienceLevel.ENTRY,
    )

    experience_years = models.PositiveIntegerField(null=True, blank=True)

    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    salary_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salary_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    currency = models.CharField(max_length=10, default="USD")

    contact_email = models.EmailField(blank=True)

    contact_phone = models.CharField(max_length=20, blank=True)

    benefits = models.JSONField(default=list, blank=True)

    deadline = models.DateField(null=True, blank=True)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = generate_unique_slug(Job, self.title)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
