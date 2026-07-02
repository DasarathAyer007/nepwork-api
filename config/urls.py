"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

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
    path("api/jobs/", include("apps.jobs.urls")),
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
