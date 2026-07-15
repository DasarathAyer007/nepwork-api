# jobs/selectors.py
from datetime import timedelta

from django.contrib.gis.db.models.functions import Distance
from django.db.models import (
    Avg,
    Count,
    Exists,
    OuterRef,
    Q,
    QuerySet,
)
from django.utils import timezone

from ..models import Job, JobApplication, JobSaved


def get_base_job_queryset(user=None) -> QuerySet:
    qs = (
        Job.objects.filter(deleted_at__isnull=True)
        .select_related("posted_by", "organization", "category", "location")
        .prefetch_related("skills_required")
        .annotate(
            total_applications=Count("applications"),
            avg_applicant_experience=Avg("applications__years_of_experience"),
        )
    )

    if user and user.is_authenticated:
        saved_sub = JobSaved.objects.filter(user=user, job=OuterRef("pk"))
        applied_sub = JobApplication.objects.filter(
            applicant=user, job=OuterRef("pk")
        )

        qs = qs.annotate(
            is_saved=Exists(saved_sub),
            has_applied=Exists(applied_sub),
        )
    return qs


def get_active_jobs(user=None) -> QuerySet:
    return get_base_job_queryset(user).filter(status=Job.JobStatus.OPEN)


def get_job_by_id(job_id, user=None) -> Job:
    return get_base_job_queryset(user).get(pk=job_id)


def get_my_jobs(user) -> QuerySet:
    """Jobs posted by the current user."""
    return get_base_job_queryset().filter(posted_by=user)


def get_saved_jobs(user) -> QuerySet:
    saved_ids = JobSaved.objects.filter(user=user).values("job_id")
    return get_active_jobs(user).filter(id__in=saved_ids)


def get_trending_jobs(user=None, days=7, user_point=None) -> QuerySet:
    """Jobs with most recent applications - placeholder.

    `user_point` (if given) nudges ordering toward jobs closer to the
    user's saved location, but only as a tie-breaker after recency of
    applications - it never outranks a genuinely more trending job.
    """
    since = timezone.now() - timedelta(days=days)
    qs = get_active_jobs(user).annotate(
        recent_applications=Count(
            "applications",
            filter=Q(applications__created_at__gte=since),
        )
    )
    if user_point:
        qs = qs.annotate(distance=Distance("location__point", user_point))
        return qs.order_by("-recent_applications", "distance", "-created_at")
    return qs.order_by("-recent_applications", "-created_at")


def get_similar_jobs(job, user=None) -> QuerySet:
    return (
        get_active_jobs(user)
        .filter(
            Q(category=job.category)
            | Q(skills_required__in=job.skills_required.all())
        )
        .exclude(pk=job.pk)
        .distinct()
    )
