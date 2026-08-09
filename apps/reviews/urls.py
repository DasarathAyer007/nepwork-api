from django.urls import path

from .views import (
    JobReviewListCreateView,
    JobReviewSummaryView,
    ReviewDetailView,
    ReviewListView,
    ServiceReviewListCreateView,
    ServiceReviewSummaryView,
)

urlpatterns = [
    path("reviews/", ReviewListView.as_view(), name="review-list"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path(
        "jobs/<uuid:job_id>/reviews/",
        JobReviewListCreateView.as_view(),
        name="job-review-list-create",
    ),
    path(
        "jobs/<uuid:job_id>/reviews/summary/",
        JobReviewSummaryView.as_view(),
        name="job-review-summary",
    ),
    path(
        "services/<uuid:service_id>/reviews/",
        ServiceReviewListCreateView.as_view(),
        name="service-review-list-create",
    ),
    path(
        "services/<uuid:service_id>/reviews/summary/",
        ServiceReviewSummaryView.as_view(),
        name="service-review-summary",
    ),
]
