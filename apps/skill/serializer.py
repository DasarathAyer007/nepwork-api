from rest_framework import serializers

from apps.skill.models import Skill


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"
