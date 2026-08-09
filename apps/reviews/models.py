from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.utils.models import SoftDeleteModel, TimeStampedModel


class Review(TimeStampedModel, SoftDeleteModel):
    reviewer = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reviews_given",
    )

    reviewee = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )

    job = models.ForeignKey(
        "jobs.Job",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    service = models.ForeignKey(
        "services.Service",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(job__isnull=False, service__isnull=True)
                    | Q(job__isnull=True, service__isnull=False)
                ),
                name="review_exactly_one_target",
            ),
            models.CheckConstraint(
                condition=~Q(reviewer=F("reviewee")),
                name="reviewer_cannot_review_themselves",
            ),
            # One review per user for a particular Job
            models.UniqueConstraint(
                fields=["reviewer", "job"],
                condition=Q(job__isnull=False),
                name="unique_review_per_reviewer_job",
            ),
            # One review per user for a particular Service
            models.UniqueConstraint(
                fields=["reviewer", "service"],
                condition=Q(service__isnull=False),
                name="unique_review_per_reviewer_service",
            ),
        ]

        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["service"]),
            models.Index(fields=["reviewee"]),
            models.Index(fields=["reviewer"]),
        ]

    def clean(self):
        super().clean()

        if (self.job is None) == (self.service is None):
            raise ValidationError(
                "A review must be linked to exactly one of job or service."
            )

        if self.reviewer == self.reviewee:
            raise ValidationError("You cannot review yourself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def target(self):
        return self.job if self.job is not None else self.service

    @property
    def target_type(self):
        return "job" if self.job is not None else "service"

    def __str__(self):
        return (
            f"{self.reviewer} → {self.reviewee} "
            f"({self.rating}★) on {self.target}"
        )
