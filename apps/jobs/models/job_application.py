from uuid import uuid7

from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class JobApplication(TimeStampedModel, SoftDeleteModel):
    class ApplicationStatus(models.TextChoices):
        APPLIED = "applied", "Applied"
        SHORTLISTED = "shortlisted", "Shortlisted"
        UNDER_REVIEW = "under_review", "Under Review"
        INTERVIEW_SCHEDULED = (
            "interview_scheduled",
            "Interview Scheduled",
        )
        INTERVIEWED = "interviewed", "Interviewed"
        OFFERED = "offered", "Offered"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="applications",
        db_index=True,
    )

    applicant = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="job_applications",
    )

    resume = models.FileField(upload_to="resumes/", blank=True, null=True)

    cover_letter = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.APPLIED,
    )

    expected_salary = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    years_of_experience = models.PositiveIntegerField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )

    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job", "applicant"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_job_application_per_applicant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.applicant} → {self.job}"
