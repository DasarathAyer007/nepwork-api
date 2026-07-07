from rest_framework import serializers

from ..models import ServiceCategory


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "description", "icon", "color", "is_active"]
