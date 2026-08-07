from rest_framework import serializers

from apps.utils.serializers import SvgIconUploadMixin

from ..models import ServiceCategory


class CategorySerializer(SvgIconUploadMixin, serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "description", "icon", "color", "is_active"]


class PopularCategorySerializer(CategorySerializer):
    count = serializers.IntegerField(read_only=True)

    class Meta(CategorySerializer.Meta):
        fields = [*CategorySerializer.Meta.fields, "count"]
