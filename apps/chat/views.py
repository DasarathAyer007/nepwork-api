from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import HasPermission

from .models import Chat, Message
from .permission import IsChatMember
from .serializers import (
    AdminChatCreateSerializer,
    AdminChatSerializer,
    AdminChatUpdateSerializer,
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


# ==========================================
# Admin Chat Endpoints (RBAC Managed)
# ==========================================


class AdminChatListView(generics.ListCreateAPIView):
    """
    GET  /api/chats/admin/ - List all system conversations with search & member filtering
    POST /api/chats/admin/ - Admin create new chat / conversation
    """

    permission_classes = [IsAuthenticated, HasPermission("communication.view")]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminChatCreateSerializer
        return AdminChatSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("communication.edit")()]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        qs = Chat.objects.prefetch_related("members", "messages").order_by(
            "-updated_at"
        )

        member_id = self.request.query_params.get("member_id")
        search = self.request.query_params.get(
            "search"
        ) or self.request.query_params.get("q")

        if member_id:
            qs = qs.filter(members__id=member_id)

        if search:
            search = search.strip()
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(members__username__icontains=search)
                | Q(members__full_name__icontains=search)
                | Q(members__email__icontains=search)
            ).distinct()

        return qs


class AdminChatDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/chats/admin/<id>/ - Retrieve conversation metadata
    PATCH  /api/chats/admin/<id>/ - Update chat (rename or change members)
    DELETE /api/chats/admin/<id>/ - Delete chat
    """

    queryset = Chat.objects.prefetch_related("members", "messages")

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminChatUpdateSerializer
        return AdminChatSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH"]:
            return [IsAuthenticated(), HasPermission("communication.edit")()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), HasPermission("communication.delete")()]
        return [IsAuthenticated(), HasPermission("communication.view")()]


class AdminChatMessageListView(generics.ListAPIView):
    """
    GET /api/chats/admin/<chat_id>/messages/ - Paginated message list for admin view
    """

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, HasPermission("communication.view")]
    pagination_class = None

    def get_queryset(self):
        chat_id = self.kwargs["chat_id"]
        get_object_or_404(Chat, id=chat_id)
        return (
            Message.objects.filter(chat_id=chat_id)
            .select_related("sender")
            .order_by("created_at")
        )


class AdminChatMessageSendView(APIView):
    """
    POST /api/chats/admin/<chat_id>/messages/send/ - Admin sends a message into chat
    """

    permission_classes = [IsAuthenticated, HasPermission("communication.edit")]

    def post(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id)

        # Automatically add admin user to chat members if not already present
        if not chat.members.filter(id=request.user.id).exists():
            chat.members.add(request.user)

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


class AdminChatMessageDeleteView(APIView):
    """
    DELETE /api/chats/admin/messages/<message_id>/ - Delete specific message
    """

    permission_classes = [
        IsAuthenticated,
        HasPermission("communication.delete"),
    ]

    def delete(self, request, message_id):
        msg = get_object_or_404(Message, id=message_id)
        msg.delete()
        return Response(
            status=status.HTTP_24_NO_CONTENT
            if hasattr(status, "HTTP_24_NO_CONTENT")
            else status.HTTP_204_NO_CONTENT
        )
