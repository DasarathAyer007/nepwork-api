from django.conf import settings
from django.db.models import Count, QuerySet
from django.utils import timezone

MAX_CANDIDATES_PER_FEED = getattr(
    settings, "RECOMMENDATION_CANDIDATE_POOL_SIZE", 500
)


class CandidateGenerator:
    """
    Pulls a manageable candidate pool from Postgres for the scorer to rank.
    Keeps DB filtering cheap (indexed status/category lookups) — never do
    per-candidate scoring logic here, that belongs in scorer.py.
    """

    def get_job_candidates(
        self, preference: dict, limit: int = MAX_CANDIDATES_PER_FEED
    ) -> QuerySet:
        from apps.jobs.models import Job

        category_ids = list(preference["job_categories"].keys())
        if not category_ids:
            return Job.objects.none()

        excluded_ids = (
            preference["job_ids_seen"] | preference["job_ids_applied"]
        )

        return (
            Job.objects.filter(
                category_id__in=category_ids, status=Job.JobStatus.OPEN
            )
            .exclude(deadline__lt=timezone.now().date())
            .exclude(id__in=excluded_ids)
            .only("id", "category_id", "created_at")
            .prefetch_related("skills_required")
            .annotate(total_applications=Count("applications"))
            .order_by("-created_at")[:limit]
        )

    def get_service_candidates(
        self, preference: dict, limit: int = MAX_CANDIDATES_PER_FEED
    ) -> QuerySet:
        from apps.services.models import Service

        category_ids = list(preference["service_categories"].keys())
        if not category_ids:
            return Service.objects.none()

        excluded_ids = (
            preference["service_ids_seen"] | preference["service_ids_requested"]
        )

        return (
            Service.objects.filter(
                category_id__in=category_ids,
                status=Service.ServiceStatus.ACTIVE,
            )
            .exclude(id__in=excluded_ids)
            .only("id", "category_id", "created_at")
            .prefetch_related("skills")
            .order_by("-created_at")[:limit]
        )
