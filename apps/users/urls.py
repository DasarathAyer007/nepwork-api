from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views.profile import UpdateProfileView

from .views.auth import (
    FacebookLoginView,
    GoogleLoginView,
)
from .views.users import (
    LoginView,
    OnboardingView,
    ProfileDetailView,
    RegisterView,
    ResendOTPView,
    UserLocationView,
    VerifyOTPView,
)

urlpatterns = [
    path("register", RegisterView.as_view()),
    path("login", LoginView.as_view()),
    path("token/refresh", TokenRefreshView.as_view()),
    path("verify-otp", VerifyOTPView.as_view()),
    path("resend-otp", ResendOTPView.as_view()),
    path("onboarding", OnboardingView.as_view()),
    path("profile/<uuid:id>", ProfileDetailView.as_view()),
    path("profile/<str:username>", ProfileDetailView.as_view()),
    path("<uuid:user_id>/location", UserLocationView.as_view()),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("auth/facebook/", FacebookLoginView.as_view(), name="facebook-login"),
    path(
        "profile/update/",
        UpdateProfileView.as_view(),
        name="update-profile",
    ),
]
