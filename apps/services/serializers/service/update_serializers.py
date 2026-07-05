from rest_framework import serializers

from apps.locations.serializers import LocationWriteSerializer


class ServiceLocationUpdateSerializer(serializers.Serializer):
    location = LocationWriteSerializer(write_only=True)

    def update(self, instance, validated_data):
        loc_data = validated_data["location"]
        if instance.location:
            loc_serializer = LocationWriteSerializer(
                instance.location, data=loc_data, partial=True
            )
        else:
            loc_serializer = LocationWriteSerializer(data=loc_data)
        loc_serializer.is_valid(raise_exception=True)
        instance.location = loc_serializer.save()
        instance.save(update_fields=["location"])
        return instance
