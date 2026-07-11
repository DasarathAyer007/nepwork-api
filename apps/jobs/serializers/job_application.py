from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.jobs.models.jobs import Job

from ..models import JobApplication

User = get_user_model()


class JobApplicationJobSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "slug",
            "thumbnail",
            "status",
            "posted_by",
            "posted_by_name",
        ]

    def get_posted_by_name(self, obj):
        return str(obj.posted_by) if obj.posted_by else None


class JobApplicationUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "full_name", "profile_picture"]


class JobApplicationReadSerializer(serializers.ModelSerializer):
    applicant = JobApplicationUserSerializer(read_only=True)
    job = JobApplicationJobSerializer(read_only=True)
    reviewed_by = JobApplicationUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "applicant",
            "resume",
            "cover_letter",
            "status",
            "expected_salary",
            "years_of_experience",
            "reviewed_by",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobApplicationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            "job",
            "resume",
            "cover_letter",
            "expected_salary",
            "years_of_experience",
            "notes",
            "expected_salary",
        ]

    def validate_job(self, value):
        if value.status != Job.JobStatus.OPEN:
            raise serializers.ValidationError(
                "Job is not open for applications."
            )
        if value.posted_by == self.context["request"].user:
            raise serializers.ValidationError("Cannot apply to your own job.")
        return value

    def create(self, validated_data):
        return JobApplication.objects.create(**validated_data)


class StatusTransitionSerializer(serializers.Serializer):
    pass  # Could include notes field
