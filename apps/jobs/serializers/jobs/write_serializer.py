from rest_framework import serializers

from apps.locations.serializers import LocationWriteSerializer
from apps.skill.services import SkillService
from apps.utils.serializers import MultipartJSONFieldsMixin

from ...models import Job


class JobWriteSerializer(MultipartJSONFieldsMixin, serializers.ModelSerializer):
    json_fields = ("skills_required",)

    location = serializers.JSONField(required=False, write_only=True)
    skills_required = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True),
        required=True,
        write_only=True,
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "slug",
            "description",
            "thumbnail",
            "organization",
            "job_type",
            "work_mode",
            "status",
            "category",
            "skills_required",
            "requirements",
            "experience_level",
            "experience_years",
            "location",
            "salary_min",
            "salary_max",
            "currency",
            "contact_email",
            "contact_phone",
            "benefits",
            "deadline",
        ]
        extra_kwargs = {"slug": {"required": False}}

    def validate(self, attrs):
        if (
            attrs.get("salary_min")
            and attrs.get("salary_max")
            and attrs["salary_min"] > attrs["salary_max"]
        ):
            raise serializers.ValidationError(
                {"salary_min": "Min must be <= max."}
            )
        return attrs

    def create(self, validated_data):
        location_data = validated_data.pop("location", None)
        skills_required = validated_data.pop("skills_required", [])
        job = Job.objects.create(**validated_data)
        if skills_required:
            job.skills_required.set(
                SkillService.get_or_create_skills(skills_required)
            )
        if location_data:
            loc_serializer = LocationWriteSerializer(data=location_data)
            loc_serializer.is_valid(raise_exception=True)
            job.location = loc_serializer.save()
            job.save(update_fields=["location"])
        return job

    def update(self, instance, validated_data):
        location_data = validated_data.pop("location", None)
        skills_required = validated_data.pop("skills_required", None)

        instance = super().update(instance, validated_data)

        if skills_required is not None:
            instance.skills_required.set(
                SkillService.get_or_create_skills(skills_required)
            )

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
