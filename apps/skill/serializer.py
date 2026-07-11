from rest_framework import serializers

from apps.skill.models import Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class SkillUsageSerializer(serializers.ModelSerializer):
    """Skill serializer that also exposes usage counts.

    Only valid against querysets annotated with `personal_count`,
    `job_count`, `service_count` and `total_count` (see
    `apps.skill.views.annotated_skill_queryset`).
    """

    job_count = serializers.IntegerField(read_only=True)
    service_count = serializers.IntegerField(read_only=True)
    personal_count = serializers.IntegerField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Skill
        fields = [
            "id",
            "name",
            "job_count",
            "service_count",
            "personal_count",
            "total_count",
        ]
