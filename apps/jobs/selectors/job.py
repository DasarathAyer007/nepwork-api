# jobs/selectors.py
from datetime import timedelta

from django.db.models import (
    Avg,
    BooleanField,
    Count,
    ExpressionWrapper,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
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
        saved_sub = JobSaved.objects.filter(
            user=user, job=OuterRef("pk")
        ).values("pk")[:1]
        applied_sub = JobApplication.objects.filter(
            applicant=user, job=OuterRef("pk")
        ).values("pk")[:1]

        qs = qs.annotate(
            is_saved=ExpressionWrapper(
                Q(pk__in=Subquery(saved_sub)), output_field=BooleanField()
            ),
            has_applied=ExpressionWrapper(
                Q(pk__in=Subquery(applied_sub)), output_field=BooleanField()
            ),
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


def get_trending_jobs(user=None, days=7) -> QuerySet:
    """Jobs with most recent applications - placeholder."""
    since = timezone.now() - timedelta(days=days)
    return (
        get_active_jobs(user)
        .annotate(
            recent_applications=Count(
                "applications",
                filter=Q(applications__created_at__gte=since),
            )
        )
        .order_by("-recent_applications", "-created_at")
    )


def get_recommendation_queryset(user) -> QuerySet:
    """
    Placeholder: jobs matching user's profile skills or past applications.
    Replace with actual logic.
    """
    if not user.is_authenticated:
        return get_active_jobs().none()

    # Example: exclude jobs already applied to, filter by user's skills
    applied_ids = JobApplication.objects.filter(applicant=user).values("job_id")
    # Assume user has a profile with skills ManyToMany; adjust field name
    user_skills = getattr(user, "profile", None) and user.profile.skills.all()
    qs = (
        get_active_jobs(user)
        .exclude(id__in=applied_ids)
        .exclude(posted_by=user)
    )

    if user_skills:
        qs = qs.filter(skills_required__in=user_skills).distinct()

    return qs.order_by("-total_applications", "-created_at")


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
