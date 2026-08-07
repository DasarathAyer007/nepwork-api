from rest_framework import serializers

from apps.utils.serializers import SvgIconUploadMixin

from ..models import JobCategory


class JobCategorySerializer(SvgIconUploadMixin, serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ["id", "name", "description", "icon", "color", "is_active"]
