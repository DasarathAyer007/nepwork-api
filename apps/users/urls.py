from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    OnboardingView,
    ProfileDetailView,
    RegisterView,
    UserLocationView,
)

urlpatterns = [
    path("register", RegisterView.as_view()),
    path("login", LoginView.as_view()),
    path("token/refresh", TokenRefreshView.as_view()),
    path("onboarding", OnboardingView.as_view()),
    path("profile/<uuid:id>", ProfileDetailView.as_view()),
    path("profile/<str:username>", ProfileDetailView.as_view()),
    path("<uuid:user_id>/location", UserLocationView.as_view()),
]
