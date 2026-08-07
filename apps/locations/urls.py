from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LocationViewSet, ReverseGeocodingView, SearchSuggestionView

router = DefaultRouter()
router.register(r"locations", LocationViewSet, basename="location")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "reverse-geocode/",
        ReverseGeocodingView.as_view(),
        name="reverse-geocode",
    ),
    path(
        "search-suggestions/",
        SearchSuggestionView.as_view(),
        name="search-suggestions",
    ),
]

urlpatterns += router.urls
