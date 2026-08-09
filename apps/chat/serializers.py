from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Chat, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "profile_picture", "email"]

    def get_profile_picture(self, obj) -> str | None:
        request = self.context.get("request")
        if hasattr(obj, "get_absolute_avatar_url"):
            return obj.get_absolute_avatar_url(request)
        return getattr(obj, "profile_picture", None)


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    chat_id = serializers.UUIDField(read_only=True)

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
        queryset=User.objects.all(),
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
            return MessageSerializer(last, context=self.context).data
        return None

    def get_unread_count(self, obj) -> int:
        from .services import ChatService

        request = self.context.get("request")
        user = request.user if request else self.context.get("user")
        if not user or not user.is_authenticated:
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

        chat = Chat.objects.create(chat_type=Chat.ChatType.GROUP)
        chat.members.set(members)
        return chat


class AdminChatSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    messages_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            "id",
            "name",
            "chat_type",
            "members",
            "last_message",
            "messages_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(MessageSerializer)
    def get_last_message(self, obj):
        last = obj.messages.order_by("-created_at").first()
        if last:
            return MessageSerializer(last, context=self.context).data
        return None

    def get_messages_count(self, obj) -> int:
        return obj.messages.count()


class AdminChatCreateSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, min_length=1
    )
    name = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Chat
        fields = ["name", "member_ids"]

    def create(self, validated_data):
        from .services import ChatService

        member_ids = validated_data.pop("member_ids")
        members = list(User.objects.filter(id__in=member_ids))
        if not members:
            raise serializers.ValidationError(
                "At least one valid member user is required."
            )

        name = validated_data.get("name", "").strip()

        if len(members) == 2 and not name:
            chat, _created = ChatService.get_or_create_direct_chat_sync(
                {m.id for m in members}
            )
            return chat

        chat_type = (
            Chat.ChatType.GROUP
            if (len(members) > 2 or name)
            else Chat.ChatType.DIRECT
        )
        chat = Chat.objects.create(name=name, chat_type=chat_type)
        chat.members.set(members)
        return chat


class AdminChatUpdateSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True
    )

    class Meta:
        model = Chat
        fields = ["name", "member_ids"]

    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        if "name" in validated_data:
            instance.name = validated_data["name"]
            instance.save(update_fields=["name"])

        if member_ids is not None:
            members = User.objects.filter(id__in=member_ids)
            instance.members.set(members)

        return instance


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=5000)
