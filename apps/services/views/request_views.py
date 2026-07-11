# services/views_requests.py
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import ServiceRequest
from ..permissions import IsServiceRequestParticipantOrAdmin
from ..selectors.request_selectors import get_service_requests_base
from ..serializers import (
    ServiceRequestReadSerializer,
    ServiceRequestWriteSerializer,
    StatusTransitionSerializer,
)
from ..services.service_requests_services import (
    ServiceRequestQueryService,
    ServiceRequestTransitionService,
)


@extend_schema(tags=["Services/Requests"])
class ServiceRequestViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for service requests + status transitions.
    """

    permission_classes = [IsServiceRequestParticipantOrAdmin]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ServiceRequestWriteSerializer
        # For status actions we don't need a body serializer, so return something harmless
        if self.action in (
            "accept",
            "reject",
            "start_progress",
            "complete",
            "cancel",
        ):
            return StatusTransitionSerializer
        return ServiceRequestReadSerializer

    def get_queryset(self):
        qs = get_service_requests_base(user=self.request.user)
        svc = ServiceRequestQueryService(
            user=self.request.user,
            params=self.request.query_params,
        )
        return svc.apply_filters(qs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    #  Status transition actions
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._handle_transition(
            pk, ServiceRequest.ServiceRequestStatus.ACCEPTED
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._handle_transition(
            pk, ServiceRequest.ServiceRequestStatus.REJECTED
        )

    @action(detail=True, methods=["post"])
    def start_progress(self, request, pk=None):
        return self._handle_transition(
            pk, ServiceRequest.ServiceRequestStatus.IN_PROGRESS
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._handle_transition(
            pk, ServiceRequest.ServiceRequestStatus.COMPLETED
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._handle_transition(
            pk, ServiceRequest.ServiceRequestStatus.CANCELLED
        )

    def _handle_transition(self, pk, new_status):
        instance = self.get_object()
        updated = ServiceRequestTransitionService.transition(
            instance, new_status, self.request.user
        )
        return Response(ServiceRequestReadSerializer(updated).data)
