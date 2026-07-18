from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.recommendations.services.reader import RecommendationReadService
from apps.user_activity.constants import ActivityType, ObjectType
from apps.user_activity.mixins import ActivityTrackingMixin

from ..models import Job
from ..permissions import IsJobOwnerOrAdminReadOnly
from ..selectors.job import get_active_jobs
from ..serializers.jobs import (
    JobDetailSerializer,
    JobListSerializer,
    JobLocationUpdateSerializer,
    JobSalarySerializer,
    JobWriteSerializer,
)
from ..services.job import JobQueryService


@extend_schema(tags=["Jobs"])
class JobViewSet(ActivityTrackingMixin, viewsets.ModelViewSet):
    queryset = Job.objects
    permission_classes = [IsJobOwnerOrAdminReadOnly]
    lookup_field = "pk"
    activity_object_type = ObjectType.JOB

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobWriteSerializer
        if self.action == "retrieve":
            return JobDetailSerializer
        return JobListSerializer

    def get_queryset(self):
        if self.action == "list":
            svc = JobQueryService(
                user=self.request.user,
                params=self.request.query_params,
            )
            return svc.list_jobs()
        if self.action == "retrieve":
            svc = JobQueryService(user=self.request.user)
            return svc.retrieve_queryset()
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

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

    # ── Thin listing actions ────────────────────────────────
    @action(detail=False, methods=["get"])
    def near_me(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.near_me())

    @action(detail=False, methods=["get"])
    def trending(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.trending())

    @action(detail=False, methods=["get"], url_path="recommended")
    def recommended(self, request):
        if not request.user or not request.user.is_authenticated:
            raise ValidationError("Authentication required.")
        reader = RecommendationReadService()
        ordered_ids = reader.get_ranked_ids(request.user.id, "jobs", top_n=100)
        qs = reader.reorder_queryset(get_active_jobs(request.user), ordered_ids)
        return self._list_response(qs)

    @action(detail=False, methods=["get"], url_path="saved")
    def saved_jobs(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.saved())

    @action(detail=False, methods=["get"], url_path="my-jobs")
    def my_jobs(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.my_jobs())

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return Response(svc.status_counts())

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        svc = JobQueryService(user=request.user, params=request.query_params)
        qs = svc.similar(pk)
        return self._list_response(qs)

    def _list_response(self, qs):
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Jobs"])
class JobSalaryUpdateView(generics.UpdateAPIView):
    serializer_class = JobSalarySerializer
    permission_classes = [IsJobOwnerOrAdminReadOnly]
    queryset = Job.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"


@extend_schema(tags=["Jobs"])
class JobLocationUpdateView(generics.UpdateAPIView):
    serializer_class = JobLocationUpdateSerializer
    permission_classes = [IsJobOwnerOrAdminReadOnly]
    queryset = Job.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"
