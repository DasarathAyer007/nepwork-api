# jobs/views_applications.py
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import JobApplication
from ..selectors.application import get_applications_base
from ..serializers.job_application import (
    JobApplicationReadSerializer,
    JobApplicationWriteSerializer,
    StatusTransitionSerializer,
)
from ..services.job_application import (
    ApplicationTransitionService,
    JobApplicationQueryService,
)


@extend_schema(tags=["Jobs/Applications"])
class JobApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobApplicationWriteSerializer
        if self.action in (
            "shortlist",
            "under_review",
            "schedule_interview",
            "offer",
            "reject",
            "withdraw",
        ):
            return StatusTransitionSerializer
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

    # Status transitions
    @action(detail=True, methods=["post"])
    def shortlist(self, request, pk=None):
        return self._transition(
            pk, JobApplication.ApplicationStatus.SHORTLISTED
        )

    @action(detail=True, methods=["post"])
    def under_review(self, request, pk=None):
        return self._transition(
            pk, JobApplication.ApplicationStatus.UNDER_REVIEW
        )

    @action(detail=True, methods=["post"])
    def schedule_interview(self, request, pk=None):
        return self._transition(
            pk, JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED
        )

    @action(detail=True, methods=["post"])
    def offer(self, request, pk=None):
        return self._transition(pk, JobApplication.ApplicationStatus.OFFERED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(pk, JobApplication.ApplicationStatus.REJECTED)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        return self._transition(pk, JobApplication.ApplicationStatus.WITHDRAWN)

    def _transition(self, pk, new_status):
        instance = self.get_object()
        updated = ApplicationTransitionService.transition(
            instance, new_status, self.request.user
        )
        return Response(JobApplicationReadSerializer(updated).data)
