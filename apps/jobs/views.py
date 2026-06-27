from rest_framework import viewsets

from apps.jobs.permissions import IsJobOwnerOrAdmin
from apps.jobs.serializers.job_serializers import JobSerializer

from .models import Job


class JobViewSet(viewsets.ModelViewSet[Job]):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [IsJobOwnerOrAdmin]
