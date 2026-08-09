from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django_scalar import views as scalar_views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from config import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls")),
    path("api/skills/", include("apps.skill.urls")),
    path("api/locations/", include("apps.locations.urls")),
    path("api/services/", include("apps.services.urls")),
    path("api/chats/", include("apps.chat.urls")),
    path("api/jobs/", include("apps.jobs.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/user-activities/", include("apps.user_activity.urls")),
    path("api/", include("apps.admin_panel.urls")),
]

# API Documentation
urlpatterns += [
    # Scalar API Documentation,
    path("api/docs/", scalar_views.scalar_viewer, name="scalar_api_docs"),
    # Swagger UI Documentation
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    # redoc and schema endpoints
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
