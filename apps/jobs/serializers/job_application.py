from rest_framework import serializers

from apps.jobs.models.jobs import Job

from ..models import JobApplication


class JobApplicationReadSerializer(serializers.ModelSerializer):
    applicant = serializers.StringRelatedField()
    job = serializers.StringRelatedField()
    reviewed_by = serializers.StringRelatedField()

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
