from django.urls import path

from apps.users.views.profile import UpdateProfileView

from .views.admin_user import (
    AdminUserListView,
    AdminUserUpdateView,
    CandidateUserListView,
)
from .views.auth import (
    CustomTokenRefreshView,
    FacebookLoginView,
    GoogleLoginView,
    LogoutView,
)
from .views.permission import (
    PermissionListView,
    UserPermissionGrantView,
    UserPermissionListView,
    UserPermissionRevokeView,
)
from .views.role import RoleDetailView, RoleListView, RoleUpdatePermissionsView
from .views.users import (
    AdminCreateView,
    LoginView,
    MeView,
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
    path("me", MeView.as_view()),
    path("admin/create", AdminCreateView.as_view()),
    path("admin/users", AdminUserListView.as_view()),
    path("admin/users/<uuid:id>", AdminUserUpdateView.as_view()),
    path("admin/candidates", CandidateUserListView.as_view()),
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
    path("roles", RoleListView.as_view()),
    path("roles/<uuid:id>", RoleDetailView.as_view()),
    path("roles/<uuid:id>/permissions", RoleUpdatePermissionsView.as_view()),
    path("permissions", PermissionListView.as_view()),
    path("permission-overrides", UserPermissionListView.as_view()),
    path("permission-overrides/grant", UserPermissionGrantView.as_view()),
    path(
        "permission-overrides/<int:id>/revoke",
        UserPermissionRevokeView.as_view(),
    ),
]
