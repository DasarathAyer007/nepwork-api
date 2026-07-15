from rest_framework import serializers

from apps.locations.serializers import LocationReadSerializer
from apps.users.serializers.ProfileReadSerializer import ProfileReadSerializer

from ...models import Job, JobCategory


class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ["id", "name", "icon", "color"]


class JobListSerializer(serializers.ModelSerializer):
    location = LocationReadSerializer(read_only=True, allow_null=True)
    posted_by = serializers.StringRelatedField()
    category = JobCategorySerializer(read_only=True)
    skills_required = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    organization = serializers.StringRelatedField()
    total_applications = serializers.IntegerField(read_only=True)
    is_saved = serializers.BooleanField(read_only=True)
    has_applied = serializers.BooleanField(read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "slug",
            "thumbnail",
            "job_type",
            "work_mode",
            "status",
            "location",
            "posted_by",
            "organization",
            "category",
            "skills_required",
            "salary_min",
            "salary_max",
            "currency",
            "experience_level",
            "experience_years",
            "deadline",
            "total_applications",
            "is_saved",
            "has_applied",
        ]


class JobDetailSerializer(JobListSerializer):
    description = serializers.CharField()
    requirements = serializers.JSONField()
    benefits = serializers.JSONField()
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField()
    employer = ProfileReadSerializer(source="posted_by", read_only=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    is_saved = serializers.BooleanField(read_only=True)
    has_applied = serializers.BooleanField(read_only=True)

    class Meta(JobListSerializer.Meta):
        fields = [
            *JobListSerializer.Meta.fields,
            "description",
            "requirements",
            "benefits",
            "contact_email",
            "contact_phone",
            "created_at",
            "updated_at",
            "employer",
            "is_saved",
            "has_applied",
        ]
