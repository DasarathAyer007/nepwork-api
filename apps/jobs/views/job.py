from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Job
from ..permissions import IsJobOwnerOrAdminReadOnly
from ..serializers.jobs import (
    JobDetailSerializer,
    JobListSerializer,
    JobLocationUpdateSerializer,
    JobSalarySerializer,
    JobWriteSerializer,
)
from ..services.job import JobQueryService


@extend_schema(tags=["Jobs"])
class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.filter(deleted_at__isnull=True)
    permission_classes = [IsJobOwnerOrAdminReadOnly]
    lookup_field = "pk"

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
        return super().get_queryset()

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

    # ── Thin listing actions ────────────────────────────────
    @action(detail=False, methods=["get"])
    def near_me(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.near_me())

    @action(detail=False, methods=["get"])
    def trending(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.trending())

    @action(detail=False, methods=["get"])
    def recommendations(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.recommendations())

    @action(detail=False, methods=["get"], url_path="saved")
    def saved_jobs(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.saved())

    @action(detail=False, methods=["get"], url_path="my")
    def my_jobs(self, request):
        svc = JobQueryService(user=request.user, params=request.query_params)
        return self._list_response(svc.my_jobs())

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


# Separate partial update views
class JobSalaryUpdateView(generics.UpdateAPIView):
    serializer_class = JobSalarySerializer
    permission_classes = [IsJobOwnerOrAdminReadOnly]
    queryset = Job.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"


class JobLocationUpdateView(generics.UpdateAPIView):
    serializer_class = JobLocationUpdateSerializer
    permission_classes = [IsJobOwnerOrAdminReadOnly]
    queryset = Job.objects.filter(deleted_at__isnull=True)
    lookup_field = "pk"
