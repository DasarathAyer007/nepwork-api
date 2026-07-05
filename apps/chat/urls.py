# from django.urls import path
# from . import views

# urlpatterns = [
#     path("", views.ChatListCreateView.as_view()),
#     path("<uuid:chat_id>/messages/", views.MessageListCreateView.as_view()),
#     path("<uuid:chat_id>/read/", views.MarkReadView.as_view()),
# ]
from django.urls import path

from .views import (
    ChatDetailView,
    ChatListCreateView,
    MarkChatReadView,
    MessageListView,
    MessageSendView,
    MessageUnreadCountView,
)

urlpatterns = [
    path("", ChatListCreateView.as_view(), name="chat-list"),
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
