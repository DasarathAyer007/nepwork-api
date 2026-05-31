from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, ProfileCreate, ProfileGet, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("profile/", ProfileCreate.as_view()),
    path("profile/<uuid:user_id>/", ProfileGet.as_view()),
]
