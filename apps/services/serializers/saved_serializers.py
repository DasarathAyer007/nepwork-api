from rest_framework import serializers

from ..models import ServiceSaved


class ServiceSavedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceSaved
        fields = ["id", "user", "service", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class ServiceSavedCreateSerializer(serializers.Serializer):
    service_id = serializers.UUIDField()
