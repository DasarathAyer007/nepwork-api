from django.urls import path

from .views import (
    PopularSkillsView,
    SkillAdminListView,
    SkillDetailView,
    SkillListView,
)

urlpatterns = [
    path("popular/", PopularSkillsView.as_view()),
    path("manage/", SkillAdminListView.as_view()),
    path("<uuid:pk>/", SkillDetailView.as_view()),
    path("", SkillListView.as_view()),
]
