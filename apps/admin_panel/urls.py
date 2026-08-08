from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SlidingImageViewSet

router = DefaultRouter()
router.register(r"sliding-images", SlidingImageViewSet, basename="slidingimage")

urlpatterns = [
    path("", include(router.urls)),
]
