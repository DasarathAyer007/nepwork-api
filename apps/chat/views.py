# from rest_framework import generics, permissions, status
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from django.contrib.auth import get_user_model
# from .models import Chat, Message
# from .serializers import ChatSerializer, MessageSerializer

# User = get_user_model()


# class ChatListCreateView(generics.ListCreateAPIView):
#     serializer_class = ChatSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Chat.objects.filter(members=self.request.user)

#     def perform_create(self, serializer):
#         chat = serializer.save()
#         chat.members.add(self.request.user)
#         # Add other members via request data
#         member_ids = self.request.data.get("member_ids", [])
#         for uid in member_ids:
#             try:
#                 chat.members.add(User.objects.get(id=uid))
#             except User.DoesNotExist:
#                 continue


# class MessageListCreateView(generics.ListCreateAPIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def get_queryset(self):
#         return Message.objects.filter(
#             chat_id=self.kwargs["chat_id"], chat__members=self.request.user
#         )

#     def get_serializer_class(self):
#         if self.request.method == "POST":
#             return MessageSerializer
#         return MessageSerializer

#     def perform_create(self, serializer):
#         serializer.save(
#             sender=self.request.user, chat_id=self.kwargs["chat_id"]
#         )


# class MarkReadView(APIView):
#     permission_classes = [permissions.IsAuthenticated]

#     def post(self, request, chat_id):
#         Message.objects.filter(chat_id=chat_id, is_read=False).exclude(
#             sender=request.user
#         ).update(is_read=True)
#         return Response({"status": "marked read"})


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


class ChatListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/chats/         - list all chats the authenticated user belongs to
    POST /api/chats/         - create a new chat
    """

    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated]

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

    def get_queryset(self):
        return self.request.user.chats.prefetch_related("members")


class MessageListView(generics.ListAPIView):
    """
    GET /api/chats/<chat_id>/messages/   - paginated message history
    """

    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsChatMember]

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
    Real-time delivery is handled via WebSocket (chat.send).
    """

    permission_classes = [IsAuthenticated, IsChatMember]

    def post(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id, members=request.user)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = Message.objects.create(
            chat=chat,
            sender=request.user,
            content=serializer.validated_data["content"],
        )
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class MarkChatReadView(APIView):
    """
    POST /api/chats/<chat_id>/read/   mark all messages in a chat as read
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, chat_id):
        get_object_or_404(Chat, id=chat_id, members=request.user)
        updated = (
            Message.objects.filter(
                chat_id=chat_id,
                is_read=False,
            )
            .exclude(sender=request.user)
            .update(is_read=True)
        )
        return Response({"marked_read": updated})


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
