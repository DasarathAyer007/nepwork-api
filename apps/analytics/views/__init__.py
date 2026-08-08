from .dashboard_views import DashboardSummaryView
from .jobs_views import (
    JobsCategoriesView,
    JobsDeadlineHealthView,
    JobsFunnelView,
    JobsStatusBreakdownView,
    JobsTrendView,
)
from .services_views import (
    ServicesAvailabilityBreakdownView,
    ServicesCategoriesView,
    ServicesFunnelView,
    ServicesStatusBreakdownView,
    ServicesTrendView,
)

__all__ = [
    "DashboardSummaryView",
    "JobsCategoriesView",
    "JobsDeadlineHealthView",
    "JobsFunnelView",
    "JobsStatusBreakdownView",
    "JobsTrendView",
    "ServicesAvailabilityBreakdownView",
    "ServicesCategoriesView",
    "ServicesFunnelView",
    "ServicesStatusBreakdownView",
    "ServicesTrendView",
]
