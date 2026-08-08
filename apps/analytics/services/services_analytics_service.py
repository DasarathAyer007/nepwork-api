from django.db.models import Count

from apps.services.models import Service, ServiceRequest

from ..selectors.services_selectors import (
    get_service_requests_for_analytics,
    get_services_for_analytics,
)
from ..utils import (
    conversion_rate,
    growth_pct,
    previous_period,
    status_counts,
    trend_series,
)

# Ordered so consecutive pairs map directly to the funnel's conversion
# stages; REJECTED/CANCELLED are terminal drop-off states, not funnel steps.
FUNNEL_STAGES = [
    ServiceRequest.ServiceRequestStatus.OPEN,
    ServiceRequest.ServiceRequestStatus.ACCEPTED,
    ServiceRequest.ServiceRequestStatus.IN_PROGRESS,
    ServiceRequest.ServiceRequestStatus.COMPLETED,
]
DROP_OFF_STATUSES = [
    ServiceRequest.ServiceRequestStatus.REJECTED,
    ServiceRequest.ServiceRequestStatus.CANCELLED,
]


class ServicesAnalyticsService:
    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.category = self.params.get("category")

    def trend(self, date_from, date_to, granularity) -> list[dict]:
        qs = get_services_for_analytics(category=self.category)
        return trend_series(qs, "created_at", date_from, date_to, granularity)

    def status_breakdown(self) -> dict:
        qs = get_services_for_analytics(category=self.category)
        return status_counts(qs, Service.ServiceStatus.choices)

    def availability_breakdown(self) -> dict:
        qs = get_services_for_analytics(category=self.category)
        return status_counts(
            qs, Service.AvailabilityStatus.choices, field="availability_status"
        )

    def funnel(self, date_from, date_to) -> dict:
        qs = get_service_requests_for_analytics(category=self.category).filter(
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
                "open_to_accepted": conversion_rate(
                    counts.get(ServiceRequest.ServiceRequestStatus.ACCEPTED, 0),
                    counts.get(ServiceRequest.ServiceRequestStatus.OPEN, 0),
                ),
                "accepted_to_in_progress": conversion_rate(
                    counts.get(
                        ServiceRequest.ServiceRequestStatus.IN_PROGRESS, 0
                    ),
                    counts.get(ServiceRequest.ServiceRequestStatus.ACCEPTED, 0),
                ),
                "in_progress_to_completed": conversion_rate(
                    counts.get(
                        ServiceRequest.ServiceRequestStatus.COMPLETED, 0
                    ),
                    counts.get(
                        ServiceRequest.ServiceRequestStatus.IN_PROGRESS, 0
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
        # Deliberately a fresh, unannotated queryset (not
        # get_services_for_analytics) so the category-level Count()
        # aggregations below aren't skewed by get_base_service_queryset's
        # own per-row annotations joining into the GROUP BY.
        qs = (
            Service.objects.filter(deleted_at__isnull=True)
            .values("category_id", "category__name")
            .annotate(
                service_count=Count("id", distinct=True),
                request_count=Count("service_requests", distinct=True),
            )
            .exclude(category_id__isnull=True)
        )

        rows = list(qs)
        for row in rows:
            row["conversion_rate"] = conversion_rate(
                row["request_count"], row["service_count"]
            )

        if sort == "conversion":
            rows.sort(key=lambda r: r["conversion_rate"] or 0, reverse=True)
        else:
            rows.sort(key=lambda r: r["service_count"], reverse=True)

        return [
            {
                "category_id": row["category_id"],
                "category_name": row["category__name"],
                "service_count": row["service_count"],
                "request_count": row["request_count"],
                "conversion_rate": row["conversion_rate"],
            }
            for row in rows[:limit]
        ]

    def summary(self, date_from, date_to) -> dict:
        prev_from, prev_to = previous_period(date_from, date_to)
        services_qs = get_services_for_analytics(category=self.category)
        current_count = services_qs.filter(
            created_at__date__gte=date_from, created_at__date__lte=date_to
        ).count()
        previous_count = services_qs.filter(
            created_at__date__gte=prev_from, created_at__date__lte=prev_to
        ).count()

        requests_qs = get_service_requests_for_analytics(
            category=self.category
        ).filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
        requests_total = requests_qs.count()
        completed_total = requests_qs.filter(
            status=ServiceRequest.ServiceRequestStatus.COMPLETED
        ).count()

        return {
            "total": services_qs.count(),
            "active": services_qs.filter(
                status=Service.ServiceStatus.ACTIVE
            ).count(),
            "new_this_period": current_count,
            "growth_pct_vs_prev_period": growth_pct(
                current_count, previous_count
            ),
            "requests_total": requests_total,
            "conversion_open_to_completed_pct": conversion_rate(
                completed_total, requests_total
            ),
        }
