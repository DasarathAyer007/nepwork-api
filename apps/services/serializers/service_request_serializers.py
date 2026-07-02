from rest_framework import serializers

from apps.locations.serializers import (
    LocationSerializer,
    LocationWriteSerializer,
)

from ..models import ServiceRequest


class ServiceRequestReadSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    service = serializers.StringRelatedField()
    location = LocationSerializer(read_only=True, allow_null=True)

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "user",
            "service",
            "status",
            "priority",
            "budget",
            "currency",
            "preferred_date",
            "preferred_time",
            "estimated_duration_hours",
            "is_negotiable",
            "request_message",
            "response_message",
            "location",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class ServiceRequestWriteSerializer(serializers.ModelSerializer):
    location = LocationWriteSerializer(required=False, write_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            "service",
            "request_message",
            "priority",
            "budget",
            "currency",
            "preferred_date",
            "preferred_time",
            "estimated_duration_hours",
            "is_negotiable",
            "location",
        ]

    def validate_service(self, value):
        # Ensure service is active and not the user's own
        if value.user == self.context["request"].user:
            raise serializers.ValidationError(
                "You cannot request your own service."
            )
        if value.status != "active":
            raise serializers.ValidationError("Service is not active.")
        return value

    def create(self, validated_data):
        location_data = validated_data.pop("location", None)
        request_obj = ServiceRequest.objects.create(**validated_data)
        if location_data:
            loc_serializer = LocationWriteSerializer(data=location_data)
            loc_serializer.is_valid(raise_exception=True)
            request_obj.location = loc_serializer.save()
            request_obj.save(update_fields=["location"])
        return request_obj

    def update(self, instance, validated_data):
        location_data = validated_data.pop("location", None)
        instance = super().update(instance, validated_data)
        if location_data is not None:
            if location_data:
                if instance.location:
                    loc_serializer = LocationWriteSerializer(
                        instance.location, data=location_data, partial=True
                    )
                else:
                    loc_serializer = LocationWriteSerializer(data=location_data)
                loc_serializer.is_valid(raise_exception=True)
                instance.location = loc_serializer.save()
                instance.save(update_fields=["location"])
            else:
                instance.location = None
                instance.save(update_fields=["location"])
        return instance


# For status transitions, simple serializers
class StatusTransitionSerializer(serializers.Serializer):
    pass
