from __future__ import annotations

from uuid import UUID

from django.db.models import Avg, Count, QuerySet

from .models import Review

RATING_CHOICES = (1, 2, 3, 4, 5)


def get_review_queryset() -> QuerySet[Review]:
    return Review.objects.select_related(
        "reviewer",
        "reviewee",
        "job",
        "service",
    )


def get_job_reviews(job_id: UUID | str) -> QuerySet[Review]:
    return get_review_queryset().filter(job_id=job_id)


def get_service_reviews(service_id: UUID | str) -> QuerySet[Review]:
    return get_review_queryset().filter(service_id=service_id)


def get_review_by_id(review_id: UUID | str) -> Review | None:
    return get_review_queryset().filter(pk=review_id).first()


def user_has_reviewed_job(reviewer_id: UUID | str, job_id: UUID | str) -> bool:
    return (
        get_review_queryset()
        .filter(reviewer_id=reviewer_id, job_id=job_id)
        .exists()
    )


def user_has_reviewed_service(
    reviewer_id: UUID | str, service_id: UUID | str
) -> bool:
    return (
        get_review_queryset()
        .filter(reviewer_id=reviewer_id, service_id=service_id)
        .exists()
    )


def get_review_stats(queryset: QuerySet[Review]) -> dict:
    aggregates = queryset.aggregate(
        average_rating=Avg("rating"),
        total_reviews=Count("id"),
    )

    # One grouped query instead of 5 separate COUNT(*) queries.
    distribution_rows = queryset.values("rating").annotate(count=Count("id"))
    distribution = {str(r): 0 for r in RATING_CHOICES}
    for row in distribution_rows:
        distribution[str(row["rating"])] = row["count"]

    average_rating = aggregates["average_rating"]

    return {
        "average_rating": round(average_rating, 2) if average_rating else 0.0,
        "total_reviews": aggregates["total_reviews"],
        "rating_distribution": distribution,
    }


def get_job_review_stats(job_id: UUID | str) -> dict:
    return get_review_stats(get_job_reviews(job_id))


def get_service_review_stats(service_id: UUID | str) -> dict:
    return get_review_stats(get_service_reviews(service_id))
