from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    JobApplicationViewSet,
    JobCategoryViewSet,
    JobLocationUpdateView,
    JobSalaryUpdateView,
    JobSavedViewSet,
    JobViewSet,
    SearchSuggestionView,
)

router = DefaultRouter()
router.register(r"category", JobCategoryViewSet, basename="jobcategory")
router.register(
    r"applications", JobApplicationViewSet, basename="jobapplication"
)
router.register(r"saved", JobSavedViewSet, basename="jobsaved")
router.register(r"", JobViewSet, basename="job")

urlpatterns = [
    path("jobs/<uuid:pk>/salary/", JobSalaryUpdateView.as_view()),
    path("jobs/<uuid:pk>/location/", JobLocationUpdateView.as_view()),
    path("search-suggestions/", SearchSuggestionView.as_view()),
    path("", include(router.urls)),
]
