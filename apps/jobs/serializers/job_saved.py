# jobs/serializers_saved.py
from rest_framework import serializers

from ..models import JobSaved


class JobSavedSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSaved
        fields = ["id", "user", "job", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class JobSavedCreateSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
