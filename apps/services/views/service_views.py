# services/views.py

from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.recommendations.services.reader import RecommendationReadService
from apps.user_activity.constants import ActivityType, ObjectType
from apps.user_activity.mixins import ActivityTrackingMixin

from ..models import Service
from ..permissions import IsServiceOwnerOrAdmin
from ..selectors.services_selectors import get_active_services
from ..serializers import (
    ServiceDetailSerializer,
    ServiceListSerializer,
    ServiceLocationUpdateSerializer,
    ServicePricingSerializer,
    ServiceRadiusSerializer,
    ServiceWriteSerializer,
)
from ..services.service_services import ServiceQueryService


@extend_schema(tags=["Services"])
class ServiceViewSet(ActivityTrackingMixin, viewsets.ModelViewSet):
    """
    Basic CRUD with listing .
    """

    queryset = Service.objects.filter(deleted_at__isnull=True)
    permission_classes = [IsServiceOwnerOrAdmin]
    lookup_field = "pk"
    activity_object_type = ObjectType.SERVICE

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ServiceWriteSerializer
        if self.action == "retrieve":
            return ServiceDetailSerializer
        return ServiceListSerializer

    def get_queryset(self):
        if self.action == "list":
            svc = ServiceQueryService(
                user=self.request.user,
                params=self.request.query_params,
            )
            return svc.list_services()
        if self.action == "retrieve":
            svc = ServiceQueryService(user=self.request.user)
            return svc.retrieve_queryset()
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        activity_type = (
            ActivityType.CLICK
            if request.query_params.get("source") == "recommended"
            else ActivityType.VIEW
        )
        self.track_activity(activity_type, object_id=kwargs.get("pk"))
        return response

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        search = request.query_params.get("search")
        if search:
            self.track_activity(
                ActivityType.SEARCH,
                object_type=None,
                metadata={"keyword": search},
            )
        return response

    # Listing methods
    @action(detail=False, methods=["get"])
    def near_me(self, request):
        svc = ServiceQueryService(
            user=request.user, params=request.query_params
        )
        qs = svc.near_me()
        return self._list_response(qs)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        svc = ServiceQueryService(
            user=request.user, params=request.query_params
        )
        return self._list_response(svc.trending())

    @action(detail=False, methods=["get"], url_path="recommended")
    def recommended(self, request):
        if not request.user or not request.user.is_authenticated:
            raise ValidationError("Authentication required.")
        reader = RecommendationReadService()
        ordered_ids = reader.get_ranked_ids(
            request.user.id, "services", top_n=100
        )
        qs = reader.reorder_queryset(
            get_active_services(request.user), ordered_ids
        )
        return self._list_response(qs)

    @action(detail=False, methods=["get"], url_path="saved")
    def saved_services(self, request):
        svc = ServiceQueryService(
            user=request.user, params=request.query_params
        )
        return self._list_response(svc.saved())

    @action(detail=False, methods=["get"], url_path="my")
    def my_services(self, request):
        svc = ServiceQueryService(
            user=request.user, params=request.query_params
        )
        return self._list_response(svc.my_services())

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        svc = ServiceQueryService(
            user=request.user, params=request.query_params
        )
        qs = svc.similar(pk)
        return self._list_response(qs)

    def _list_response(self, qs):
        """Applies pagination and serializes the response."""
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# Separate partial update views
@extend_schema(tags=["Services"])
class ServiceRadiusUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceRadiusSerializer
    permission_classes = [IsServiceOwnerOrAdmin]
    queryset = Service.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"


@extend_schema(tags=["Services"])
class ServicePricingUpdateView(generics.UpdateAPIView):
    serializer_class = ServicePricingSerializer
    permission_classes = [IsServiceOwnerOrAdmin]
    queryset = Service.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"


@extend_schema(tags=["Services"])
class ServiceLocationUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceLocationUpdateSerializer
    permission_classes = [IsServiceOwnerOrAdmin]
    queryset = Service.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"
