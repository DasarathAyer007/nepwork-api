from rest_framework import serializers

from apps.jobs.models import Job


class JobSerializer(serializers.ModelSerializer[Job]):
    class Meta:
        model = Job
        fields = "__all__"
