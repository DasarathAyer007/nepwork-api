from apps.users.models import User

from ..utils import growth_pct, previous_period
from .jobs_analytics_service import JobsAnalyticsService
from .services_analytics_service import ServicesAnalyticsService


class DashboardSummaryService:
    """Batched KPI payload for the dashboard landing view — one call per
    domain rather than one giant query, so each section stays independently
    correct and cacheable."""

    def __init__(self, params: dict | None = None):
        self.params = params or {}

    def summary(self, date_from, date_to) -> dict:
        jobs = JobsAnalyticsService(self.params).summary(date_from, date_to)
        services = ServicesAnalyticsService(self.params).summary(
            date_from, date_to
        )
        users = self._users_summary(date_from, date_to)

        return {
            "jobs": jobs,
            "services": services,
            "users": users,
            "period": {
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
        }

    def _users_summary(self, date_from, date_to) -> dict:
        prev_from, prev_to = previous_period(date_from, date_to)
        qs = User.objects.all()
        current_count = qs.filter(
            date_joined__date__gte=date_from, date_joined__date__lte=date_to
        ).count()
        previous_count = qs.filter(
            date_joined__date__gte=prev_from, date_joined__date__lte=prev_to
        ).count()

        return {
            "total": qs.count(),
            "new_this_period": current_count,
            "growth_pct_vs_prev_period": growth_pct(
                current_count, previous_count
            ),
        }
