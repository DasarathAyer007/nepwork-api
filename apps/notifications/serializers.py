from rest_framework import serializers

from .models import Notification


class NotificationSenderSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    sender = NotificationSenderSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "sender",
            "notification_type",
            "title",
            "message",
            "entity_type",
            "entity_id",
            "data",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
