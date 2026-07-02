from rest_framework import serializers

from apps.locations.serializer import (
    LocationWriteSerializer,
)
from apps.skill.services import SkillService

from ...models import Service


class ServiceWriteSerializer(serializers.ModelSerializer):
    location = LocationWriteSerializer(required=False, write_only=True)
    skills = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True),
        required=True,
        write_only=True,
    )
    available_from = serializers.TimeField(required=False, allow_null=True)
    available_to = serializers.TimeField(required=False, allow_null=True)

    class Meta:
        model = Service
        fields = [
            "title",
            "slug",
            "description",
            "thumbnail",
            "category",
            "availability_status",
            "location",
            "price_type",
            "status",
            "price",
            "currency",
            "skills",
            "radius_km",
            "available_from",
            "available_to",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate(self, attrs):
        if attrs.get("price_type") == Service.PriceType.FIXED and not attrs.get(
            "price"
        ):
            raise serializers.ValidationError(
                {"price": "Required for fixed price."}
            )
        return attrs

    def create(self, validated_data):
        location_data = validated_data.pop("location", None)
        skills = validated_data.pop("skills", [])
        service = Service.objects.create(**validated_data)
        if skills:
            service.skills.set(SkillService.get_or_create_skills(skills))
        if location_data:
            loc_serializer = LocationWriteSerializer(data=location_data)
            loc_serializer.is_valid(raise_exception=True)
            service.location = loc_serializer.save()
            service.save(update_fields=["location"])
        return service

    def update(self, instance, validated_data):
        location_data = validated_data.pop("location", None)
        skills = validated_data.pop("skills", None)

        instance = super().update(instance, validated_data)

        if skills is not None:
            instance.skills.set(skills)

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
