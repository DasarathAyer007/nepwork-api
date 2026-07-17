from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chat, Message
from .permission import IsChatMember
from .serializers import (
    ChatSerializer,
    MessageSerializer,
    SendMessageSerializer,
    User,
)
from .services import ChatService


class ChatListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/chats/         - list all chats the authenticated user belongs to
    POST /api/chats/         - create a new chat
    """

    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    pagination_class = None  # Disable pagination for chat list

    def get_queryset(self):
        return (
            self.request.user.chats.prefetch_related("members")
            .prefetch_related("messages")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        chat = serializer.save()
        # Ensure the creator is always a member
        chat.members.add(self.request.user)


class ChatDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/chats/<id>/   - retrieve chat details
    PATCH  /api/chats/<id>/   - update chat name
    DELETE /api/chats/<id>/   - leave / delete chat
    """

    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsChatMember]
    pagination_class = None

    def get_queryset(self):
        return self.request.user.chats.prefetch_related("members")


class MessageListView(generics.ListAPIView):
    """
    GET /api/chats/<chat_id>/messages/   - paginated message history
    """

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsChatMember]
    pagination_class = None

    def get_queryset(self):
        chat_id = self.kwargs["chat_id"]
        # Verify membership via IsChatMember permission on the parent chat
        get_object_or_404(Chat, id=chat_id, members=self.request.user)
        return (
            Message.objects.filter(chat_id=chat_id)
            .select_related("sender")
            .order_by("created_at")
        )


class MessageSendView(APIView):
    """
    POST /api/chats/<chat_id>/messages/send/

    HTTP fallback for sending a message (e.g. file uploads, offline queuing).
    Goes through the same ChatService call and broadcast as the WebSocket
    `chat.send` path, so recipients get it live regardless of which path
    the sender used.
    """

    permission_classes = [IsAuthenticated, IsChatMember]

    def post(self, request, chat_id):
        get_object_or_404(Chat, id=chat_id, members=request.user)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = ChatService.create_message_sync(
            sender=request.user,
            chat_id=chat_id,
            content=serializer.validated_data["content"],
        )

        member_ids = ChatService.get_member_ids_sync(chat_id)
        channel_layer = get_channel_layer()
        for member_id in member_ids:
            async_to_sync(channel_layer.group_send)(
                f"user_{member_id}",
                {"type": "chat_message", "payload": message},
            )

        return Response(message, status=status.HTTP_201_CREATED)


class MarkChatReadView(APIView):
    """
    POST /api/chats/<chat_id>/read/   mark all messages in a chat as read

    Goes through the same ChatService call and broadcast as the WebSocket
    `chat.read` path, so every member's badge updates live regardless of
    which path the reader used.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        get_object_or_404(Chat, id=chat_id, members=request.user)

        updated_count, member_unread_counts = (
            ChatService.mark_chat_read_and_get_unread_counts_sync(
                user=request.user, chat_id=chat_id
            )
        )

        channel_layer = get_channel_layer()
        for entry in member_unread_counts:
            async_to_sync(channel_layer.group_send)(
                f"user_{entry['member_id']}",
                {
                    "type": "chat_read_confirmed",
                    "payload": {
                        "chat_id": str(chat_id),
                        "reader_id": str(request.user.id),
                        "marked_read": updated_count,
                        "unread_count": entry["unread_count"],
                    },
                },
            )

        return Response({"marked_read": updated_count})


class ChatWithUserView(generics.RetrieveAPIView):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        other_user = get_object_or_404(User, pk=self.kwargs["user_id"])

        chat = (
            self.request.user.chats.filter(members=other_user)
            .prefetch_related("members")
            .prefetch_related("messages")
            .first()
        )

        if chat is None:
            raise NotFound("Chat not found.")

        return chat


class MessageUnreadCountView(APIView):
    """
    GET /api/chats/count/   get the total number of unread messages across all chats
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {"unread_count": ChatService.get_unread_count_sync(request.user)}
        )
