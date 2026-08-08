from django.db.models import Count
from django.utils import timezone

from apps.jobs.models import Job, JobApplication

from ..selectors.jobs_selectors import (
    get_job_applications_for_analytics,
    get_jobs_for_analytics,
)
from ..utils import (
    conversion_rate,
    growth_pct,
    previous_period,
    status_counts,
    trend_series,
)

# Ordered so consecutive pairs map directly to the funnel's conversion
# stages; REJECTED/WITHDRAWN are terminal drop-off states, not funnel steps.
FUNNEL_STAGES = [
    JobApplication.ApplicationStatus.APPLIED,
    JobApplication.ApplicationStatus.SHORTLISTED,
    JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED,
    JobApplication.ApplicationStatus.OFFERED,
]
DROP_OFF_STATUSES = [
    JobApplication.ApplicationStatus.REJECTED,
    JobApplication.ApplicationStatus.WITHDRAWN,
]


class JobsAnalyticsService:
    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.category = self.params.get("category")

    def trend(self, date_from, date_to, granularity) -> list[dict]:
        qs = get_jobs_for_analytics(category=self.category)
        return trend_series(qs, "created_at", date_from, date_to, granularity)

    def status_breakdown(self) -> dict:
        qs = get_jobs_for_analytics(category=self.category)
        return status_counts(qs, Job.JobStatus.choices)

    def funnel(self, date_from, date_to) -> dict:
        qs = get_job_applications_for_analytics(category=self.category).filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        )

        counts = {
            row["status"]: row["count"]
            for row in qs.values("status").annotate(count=Count("id"))
        }
        stages = [
            {"status": stage, "count": counts.get(stage, 0)}
            for stage in FUNNEL_STAGES
        ]
        drop_off_count = sum(counts.get(s, 0) for s in DROP_OFF_STATUSES)
        total = sum(counts.values())

        return {
            "stages": stages,
            "conversion_rates": {
                "applied_to_shortlisted": conversion_rate(
                    counts.get(JobApplication.ApplicationStatus.SHORTLISTED, 0),
                    counts.get(JobApplication.ApplicationStatus.APPLIED, 0),
                ),
                "shortlisted_to_interview": conversion_rate(
                    counts.get(
                        JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED, 0
                    ),
                    counts.get(JobApplication.ApplicationStatus.SHORTLISTED, 0),
                ),
                "interview_to_offered": conversion_rate(
                    counts.get(JobApplication.ApplicationStatus.OFFERED, 0),
                    counts.get(
                        JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED, 0
                    ),
                ),
            },
            "drop_off_count": drop_off_count,
            "drop_off_rate": conversion_rate(drop_off_count, total),
            "total": total,
        }

    def top_categories(
        self, limit: int = 10, sort: str = "volume"
    ) -> list[dict]:
        # Deliberately a fresh, unannotated queryset (not get_jobs_for_analytics)
        # so the category-level Count() aggregations below aren't skewed by
        # get_base_job_queryset's own per-row annotations joining into the
        # GROUP BY.
        qs = (
            Job.objects.filter(deleted_at__isnull=True)
            .values("category_id", "category__name")
            .annotate(
                job_count=Count("id", distinct=True),
                application_count=Count("applications", distinct=True),
            )
            .exclude(category_id__isnull=True)
        )

        rows = list(qs)
        for row in rows:
            row["conversion_rate"] = conversion_rate(
                row["application_count"], row["job_count"]
            )

        if sort == "conversion":
            rows.sort(key=lambda r: r["conversion_rate"] or 0, reverse=True)
        else:
            rows.sort(key=lambda r: r["job_count"], reverse=True)

        return [
            {
                "category_id": row["category_id"],
                "category_name": row["category__name"],
                "job_count": row["job_count"],
                "application_count": row["application_count"],
                "conversion_rate": row["conversion_rate"],
            }
            for row in rows[:limit]
        ]

    def summary(self, date_from, date_to) -> dict:
        prev_from, prev_to = previous_period(date_from, date_to)
        jobs_qs = get_jobs_for_analytics(category=self.category)
        current_count = jobs_qs.filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        ).count()
        previous_count = jobs_qs.filter(
            created_at__date__gte=prev_from, created_at__date__lte=prev_to
        ).count()

        applications_qs = get_job_applications_for_analytics(
            category=self.category
        ).filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        applications_total = applications_qs.count()
        offered_total = applications_qs.filter(
            status=JobApplication.ApplicationStatus.OFFERED
        ).count()

        return {
            "total": jobs_qs.count(),
            "open": jobs_qs.filter(status=Job.JobStatus.OPEN).count(),
            "new_this_period": current_count,
            "growth_pct_vs_prev_period": growth_pct(
                current_count, previous_count
            ),
            "applications_total": applications_total,
            "conversion_applied_to_offered_pct": conversion_rate(
                offered_total, applications_total
            ),
        }

    def deadline_health(self) -> dict:
        today = timezone.now().date()
        qs = get_jobs_for_analytics(category=self.category).filter(
            status=Job.JobStatus.OPEN, deadline__lt=today
        )
        return {"open_past_deadline": qs.count()}
