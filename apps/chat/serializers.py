# chat/serializers.py
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Chat, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "profile_picture", "email"]


# class ChatSerializer(serializers.ModelSerializer):
#     members = UserSerializer(many=True, read_only=True)
#     last_message = serializers.SerializerMethodField()

#     class Meta:
#         model = Chat
#         fields = ["id", "name", "members", "last_message", "created_at"]

#     def get_last_message(self, obj):
#         msg = obj.messages.last()
#         return MessageSerializer(msg).data if msg else None


# class MessageSerializer(serializers.ModelSerializer):
#     sender = UserSerializer(read_only=True)

#     class Meta:
#         model = Message
#         fields = ["id", "chat", "sender", "content", "created_at", "is_read"]
#         read_only_fields = ["sender", "created_at", "is_read"]


# class CreateMessageSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Message
#         fields = ["chat", "content"]


# class ChatSerializer(serializers.ModelSerializer):
#     members = UserSerializer(many=True, read_only=True)
#     member_ids = serializers.ListField(
#         child=serializers.IntegerField(), write_only=True, required=False
#     )
#     last_message = serializers.SerializerMethodField()
#     unread_count = serializers.SerializerMethodField()

#     class Meta:
#         model = Chat
#         fields = ["id", "name", "members", "member_ids", "last_message", "unread_count", "created_at"]
#         read_only_fields = ["id", "created_at"]

#     def get_last_message(self, obj):
#         msg = obj.messages.last()
#         return MessageSerializer(msg).data if msg else None

#     def get_unread_count(self, obj):
#         request = self.context.get("request")
#         if not request:
#             return 0
#         return obj.messages.filter(is_read=False).exclude(sender=request.user).count()

#     def create(self, validated_data):
#         member_ids = validated_data.pop("member_ids", [])
#         chat = Chat.objects.create(**validated_data)
#         request = self.context["request"]
#         chat.members.add(request.user)
#         for uid in member_ids:
#             try:
#                 chat.members.add(User.objects.get(id=uid))
#             except User.DoesNotExist:
#                 continue
#         return chat


# class SenderSerializer(serializers.Serializer):
#     id = serializers.IntegerField()
#     username = serializers.CharField()
#     # Add avatar / display_name here if your User model has them


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
        request = self.context.get("request")
        if not request:
            return 0
        return (
            obj.messages.filter(is_read=False)
            .exclude(sender=request.user)
            .count()
        )


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=5000)
