from django.urls import path

from .views.auth import (
    CustomTokenRefreshView,
    FacebookLoginView,
    GoogleLoginView,
    LogoutView,
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
    path("token/refresh", CustomTokenRefreshView.as_view()),
    path("logout", LogoutView.as_view()),
    path("verify-otp", VerifyOTPView.as_view()),
    path("resend-otp", ResendOTPView.as_view()),
    path("onboarding", OnboardingView.as_view()),
    path("profile/<uuid:id>", ProfileDetailView.as_view()),
    path("profile/<str:username>", ProfileDetailView.as_view()),
    path("<uuid:user_id>/location", UserLocationView.as_view()),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("auth/facebook/", FacebookLoginView.as_view(), name="facebook-login"),
]
