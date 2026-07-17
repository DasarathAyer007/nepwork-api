# chat/serializers.py
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Chat, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    online = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "profile_picture", "email", "online"]

    def get_online(self, obj) -> bool:
        from apps.websockets.presence import PresenceService

        return PresenceService.is_online(obj.id)


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "chat_id",
            "sender",
            "content",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "chat_id", "sender", "is_read", "created_at"]


class ChatSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    member_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=__import__("django.contrib.auth", fromlist=["get_user_model"])
        .get_user_model()
        .objects.all(),
        source="members",
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "name",
            "members",
            "member_ids",
            "last_message",
            "unread_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    @extend_schema_field(MessageSerializer)
    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if last:
            return MessageSerializer(last).data
        return None

    def get_unread_count(self, obj) -> int:
        from .services import ChatService

        request = self.context.get("request")
        user = request.user if request else self.context.get("user")
        if not user:
            return 0
        return ChatService.get_chat_unread_count_sync(obj.id, user)

    def create(self, validated_data):
        from .services import ChatService

        members = validated_data.pop("members", [])
        request = self.context.get("request")
        if request and request.user not in members:
            members.append(request.user)

        if len(set(members)) == 2:
            chat, _created = ChatService.get_or_create_direct_chat_sync(
                {m.id for m in members}
            )
            return chat

        # Group chat — no uniqueness constraint applies.
        chat = Chat.objects.create(chat_type=Chat.ChatType.GROUP)
        chat.members.set(members)
        return chat


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=5000)
