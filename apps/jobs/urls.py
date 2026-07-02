from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    JobApplicationViewSet,
    JobCategoryViewSet,
    JobLocationUpdateView,
    JobSalaryUpdateView,
    JobSavedViewSet,
    JobViewSet,
)

router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="job")
router.register(r"job-categories", JobCategoryViewSet, basename="jobcategory")
router.register(
    r"job-applications", JobApplicationViewSet, basename="jobapplication"
)
router.register(r"job-saved", JobSavedViewSet, basename="jobsaved")

urlpatterns = [
    path("", include(router.urls)),
    path("jobs/<uuid:pk>/salary/", JobSalaryUpdateView.as_view()),
    path("jobs/<uuid:pk>/location/", JobLocationUpdateView.as_view()),
]
