# jobs/views_saved.py
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.user_activity.constants import ActivityType, ObjectType
from apps.user_activity.mixins import ActivityTrackingMixin

from ..models import JobSaved
from ..serializers.job_saved import JobSavedCreateSerializer, JobSavedSerializer


@extend_schema(tags=["Jobs/Saved"])
class JobSavedViewSet(ActivityTrackingMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    activity_object_type = ObjectType.JOB
    lookup_field = "job_id"

    def get_queryset(self):
        return JobSaved.objects.filter(
            deleted_at__isnull=True, user=self.request.user
        ).select_related("job")

    def get_serializer_class(self):
        if self.action == "create":
            return JobSavedCreateSerializer
        return JobSavedSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job_id = serializer.validated_data["job_id"]
        saved, created = JobSaved.objects.get_or_create(
            user=request.user, job_id=job_id
        )
        if not created:
            return Response(
                {"detail": "Already saved."}, status=status.HTTP_200_OK
            )
        self.track_activity(ActivityType.SAVE, object_id=job_id)
        return Response(
            JobSavedSerializer(saved).data, status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        job_id = instance.job_id
        instance.hard_delete()
        self.track_activity(ActivityType.UNSAVE, object_id=job_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
