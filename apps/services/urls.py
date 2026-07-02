from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ServiceCategoryViewSet,
    ServiceLocationUpdateView,
    ServicePricingUpdateView,
    ServiceRadiusUpdateView,
    ServiceRequestViewSet,
    ServiceSavedViewSet,
    ServiceViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("", ServiceViewSet)
router.register(r"saved", ServiceSavedViewSet, basename="saved")
router.register(r"requests", ServiceRequestViewSet, basename="request")
router.register(r"category", ServiceCategoryViewSet, basename="category")

urlpatterns = [
    path("", include(router.urls)),
    path("<uuid:pk>/radius/", ServiceRadiusUpdateView.as_view()),
    path("<uuid:pk>/pricing/", ServicePricingUpdateView.as_view()),
    path("<uuid:pk>/location/", ServiceLocationUpdateView.as_view()),
]
