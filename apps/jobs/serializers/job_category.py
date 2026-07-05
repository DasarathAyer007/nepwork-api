from rest_framework import serializers

from ..models import JobCategory


class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ["id", "name", "description", "icon", "is_active"]
