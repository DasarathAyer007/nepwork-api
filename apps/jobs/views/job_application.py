# jobs/views_applications.py
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.tasks import notify_job_application
from apps.user_activity.constants import ActivityType, ObjectType
from apps.user_activity.mixins import ActivityTrackingMixin

from ..selectors.application import get_applications_base
from ..serializers.job_application import (
    EmptyActionSerializer,
    JobApplicationReadSerializer,
    JobApplicationWriteSerializer,
    StatusChangeSerializer,
)
from ..services.job_application import (
    ApplicationTransitionService,
    JobApplicationQueryService,
)


@extend_schema(tags=["Jobs/Applications"])
class JobApplicationViewSet(ActivityTrackingMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"
    activity_object_type = ObjectType.JOB

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobApplicationWriteSerializer
        if self.action == "change_status":
            return StatusChangeSerializer
        if self.action == "withdraw":
            return EmptyActionSerializer
        return JobApplicationReadSerializer

    def get_queryset(self):
        qs = get_applications_base(user=self.request.user)
        svc = JobApplicationQueryService(
            user=self.request.user,
            params=self.request.query_params,
        )
        return svc.apply_filters(qs)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)
        self.track_activity(
            ActivityType.APPLY, object_id=serializer.instance.job_id
        )
        application_id = str(serializer.instance.id)
        transaction.on_commit(
            lambda: notify_job_application.delay(application_id)
        )

    # Employer-driven status change: freely move an application to any
    # non-terminal status, optionally notifying the applicant via chat
    # and/or email.
    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        instance = self.get_object()
        serializer = StatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        updated = ApplicationTransitionService.change_status(
            instance,
            data["status"],
            request.user,
            message=data.get("message", ""),
            send_message=data.get("send_message", True),
            send_email=data.get("send_email", True),
        )
        return Response(JobApplicationReadSerializer(updated).data)

    # Applicant-driven withdrawal.
    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        instance = self.get_object()
        updated = ApplicationTransitionService.withdraw(instance, request.user)
        return Response(JobApplicationReadSerializer(updated).data)
