from django.urls import path

from .views import (
    AdminNotificationDetailView,
    AdminNotificationListView,
    NotificationDeleteView,
    NotificationLatestView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path(
        "admin/",
        AdminNotificationListView.as_view(),
        name="admin-notification-list",
    ),
    path(
        "admin/<int:pk>/",
        AdminNotificationDetailView.as_view(),
        name="admin-notification-detail",
    ),
    path(
        "latest/",
        NotificationLatestView.as_view(),
        name="notification-latest",
    ),
    path(
        "unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "read-all/",
        NotificationMarkAllReadView.as_view(),
        name="notification-read-all",
    ),
    path(
        "<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
    path(
        "<int:pk>/",
        NotificationDeleteView.as_view(),
        name="notification-delete",
    ),
]
