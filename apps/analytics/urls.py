from django.urls import path

from .views import (
    DashboardSummaryView,
    JobsCategoriesView,
    JobsDeadlineHealthView,
    JobsFunnelView,
    JobsStatusBreakdownView,
    JobsTrendView,
    ServicesAvailabilityBreakdownView,
    ServicesCategoriesView,
    ServicesFunnelView,
    ServicesStatusBreakdownView,
    ServicesTrendView,
)

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view()),
    path("jobs/trend/", JobsTrendView.as_view()),
    path("jobs/status-breakdown/", JobsStatusBreakdownView.as_view()),
    path("jobs/funnel/", JobsFunnelView.as_view()),
    path("jobs/categories/", JobsCategoriesView.as_view()),
    path("jobs/deadline-health/", JobsDeadlineHealthView.as_view()),
    path("services/trend/", ServicesTrendView.as_view()),
    path("services/status-breakdown/", ServicesStatusBreakdownView.as_view()),
    path(
        "services/availability-breakdown/",
        ServicesAvailabilityBreakdownView.as_view(),
    ),
    path("services/funnel/", ServicesFunnelView.as_view()),
    path("services/categories/", ServicesCategoriesView.as_view()),
]
