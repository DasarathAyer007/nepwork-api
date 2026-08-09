from django.urls import path

from .views import (
    AdminChatDetailView,
    AdminChatListView,
    AdminChatMessageDeleteView,
    AdminChatMessageListView,
    AdminChatMessageSendView,
    ChatDetailView,
    ChatListCreateView,
    MarkChatReadView,
    MessageListView,
    MessageSendView,
    MessageUnreadCountView,
)

urlpatterns = [
    path("", ChatListCreateView.as_view(), name="chat-list"),
    path("admin/", AdminChatListView.as_view(), name="admin-chat-list"),
    path(
        "admin/<uuid:pk>/",
        AdminChatDetailView.as_view(),
        name="admin-chat-detail",
    ),
    path(
        "admin/<uuid:chat_id>/messages/",
        AdminChatMessageListView.as_view(),
        name="admin-message-list",
    ),
    path(
        "admin/<uuid:chat_id>/messages/send/",
        AdminChatMessageSendView.as_view(),
        name="admin-message-send",
    ),
    path(
        "admin/messages/<uuid:message_id>/",
        AdminChatMessageDeleteView.as_view(),
        name="admin-message-delete",
    ),
    path(
        "unread-count/",
        MessageUnreadCountView.as_view(),
        name="message-unread-count",
    ),
    path("<uuid:pk>/", ChatDetailView.as_view(), name="chat-detail"),
    path(
        "<uuid:chat_id>/messages/",
        MessageListView.as_view(),
        name="message-list",
    ),
    path(
        "<uuid:chat_id>/messages/send/",
        MessageSendView.as_view(),
        name="message-send",
    ),
    path("<uuid:chat_id>/read/", MarkChatReadView.as_view(), name="chat-read"),
    path(
        "with-user/<uuid:user_id>",
        ChatListCreateView.as_view(),
        name="chat-with-user",
    ),
]
