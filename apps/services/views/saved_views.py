# services/views_saved.py
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.user_activity.constants import ActivityType, ObjectType
from apps.user_activity.mixins import ActivityTrackingMixin

from ..models import ServiceSaved
from ..serializers import ServiceSavedCreateSerializer, ServiceSavedSerializer


@extend_schema(tags=["Services/Saved"])
class ServiceSavedViewSet(ActivityTrackingMixin, viewsets.ModelViewSet):
    """
    Save / unsave a service.
    """

    serializer_class = ServiceSavedSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    activity_object_type = ObjectType.SERVICE
    lookup_field = "service_id"

    def get_queryset(self):
        return ServiceSaved.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """save a service for the current user"""
        serializer = ServiceSavedCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_id = serializer.validated_data["service_id"]

        saved, created = ServiceSaved.objects.get_or_create(
            user=request.user,
            service_id=service_id,
        )
        if not created:
            return Response(
                {"detail": "Already saved."},
                status=status.HTTP_200_OK,
            )
        self.track_activity(ActivityType.SAVE, object_id=service_id)
        return Response(
            ServiceSavedSerializer(saved).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """unsave"""
        instance = self.get_object()
        if instance.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        service_id = instance.service_id
        instance.delete()
        self.track_activity(ActivityType.UNSAVE, object_id=service_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
