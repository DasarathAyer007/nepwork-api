from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.locations.serializers import LocationReadSerializer

from ...models import Service
from ..category_serializers import CategorySerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "profile_picture"]


class ServiceListSerializer(serializers.ModelSerializer):
    location = LocationReadSerializer(read_only=True, allow_null=True)
    user = serializers.StringRelatedField()
    category = CategorySerializer(read_only=True)
    skills = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    is_currently_available = serializers.BooleanField(read_only=True)
    total_applies = serializers.IntegerField(read_only=True)
    is_saved = serializers.BooleanField(read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "title",
            "slug",
            "thumbnail",
            "price_type",
            "price",
            "currency",
            "availability_status",
            "status",
            "location",
            "user",
            "category",
            "skills",
            "total_applies",
            "is_currently_available",
            "is_saved",
        ]


class ServiceDetailSerializer(ServiceListSerializer):
    description = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    radius_km = serializers.IntegerField()
    available_from = serializers.TimeField()
    available_to = serializers.TimeField()

    class Meta(ServiceListSerializer.Meta):
        fields = [
            *ServiceListSerializer.Meta.fields,
            "description",
            "created_at",
            "updated_at",
            "radius_km",
            "available_from",
            "available_to",
        ]
