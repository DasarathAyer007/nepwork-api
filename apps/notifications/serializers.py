from rest_framework import serializers

from .models import Notification


class NotificationSenderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class NotificationSerializer(serializers.ModelSerializer):
    sender = NotificationSenderSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "sender",
            "title",
            "message",
            "action_url",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
