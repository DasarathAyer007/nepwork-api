from rest_framework import serializers

from apps.users.models import User

from .models import Notification


class NotificationUserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "email", "profile_picture"]

    def get_profile_picture(self, obj: User) -> str | None:
        request = self.context.get("request")
        return obj.get_absolute_avatar_url(request)


class NotificationSerializer(serializers.ModelSerializer):
    sender = NotificationUserSerializer(read_only=True)
    recipient = NotificationUserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "sender",
            "notification_type",
            "title",
            "message",
            "entity_type",
            "entity_id",
            "data",
            "is_read",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AdminNotificationCreateSerializer(serializers.ModelSerializer):
    recipient_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Notification
        fields = [
            "recipient_id",
            "notification_type",
            "title",
            "message",
            "entity_type",
            "entity_id",
            "data",
        ]

    def create(self, validated_data):
        recipient_id = validated_data.pop("recipient_id")
        recipient = User.objects.get(id=recipient_id)
        sender = self.context["request"].user
        return Notification.objects.create(
            recipient=recipient, sender=sender, **validated_data
        )


class AdminNotificationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "notification_type",
            "title",
            "message",
            "entity_type",
            "entity_id",
            "data",
            "is_read",
        ]
