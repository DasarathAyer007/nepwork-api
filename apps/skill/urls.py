from django.urls import path

from .views import PopularSkillsView, SkillListView

urlpatterns = [
    path("popular/", PopularSkillsView.as_view()),
    path("", SkillListView.as_view()),
]
