from django.urls import path

from apps.user_activity.views import UserActivityListView, UserActivityStatsView

urlpatterns = [
    path("", UserActivityListView.as_view(), name="user-activity-list"),
    path("stats", UserActivityStatsView.as_view(), name="user-activity-stats"),
]
