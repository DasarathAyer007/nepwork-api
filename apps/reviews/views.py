from __future__ import annotations

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors
from .filters import ReviewFilter
from .permissions import IsReviewOwnerOrAdmin
from .serializers import (
    ReviewCreateSerializer,
    ReviewDetailSerializer,
    ReviewListSerializer,
    ReviewUpdateSerializer,
)
from .services import ReviewService

ORDERING_FIELDS = ["created_at", "rating"]
DEFAULT_ORDERING = ["-created_at"]


class ReviewListView(generics.ListAPIView):
    serializer_class = ReviewListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReviewFilter
    ordering_fields = ORDERING_FIELDS
    ordering = DEFAULT_ORDERING

    def get_queryset(self):
        return selectors.get_review_queryset()


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsReviewOwnerOrAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        return selectors.get_review_queryset()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ReviewUpdateSerializer
        return ReviewDetailSerializer

    def perform_update(self, serializer):
        review = ReviewService.update_review(
            review=self.get_object(),
            user=self.request.user,
            **serializer.validated_data,
        )
        serializer.instance = review

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        output = ReviewDetailSerializer(
            serializer.instance, context=self.get_serializer_context()
        )
        return Response(output.data)

    def perform_destroy(self, instance):
        ReviewService.delete_review(review=instance, user=self.request.user)


class _BaseTargetReviewListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ReviewFilter
    ordering_fields = ORDERING_FIELDS
    ordering = DEFAULT_ORDERING

    url_kwarg: str = ""  # e.g. "job_id" / "service_id"

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReviewCreateSerializer
        return ReviewListSerializer

    def get_target_id(self):
        return self.kwargs[self.url_kwarg]

    def get_queryset(self):
        raise NotImplementedError

    def create_review(self, *, reviewer, target_id, rating, comment):
        raise NotImplementedError

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = self.create_review(
            reviewer=request.user,
            target_id=self.get_target_id(),
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data.get("comment", ""),
        )

        output = ReviewDetailSerializer(
            review, context=self.get_serializer_context()
        )
        headers = self.get_success_headers(output.data)
        return Response(
            output.data, status=status.HTTP_201_CREATED, headers=headers
        )


class JobReviewListCreateView(_BaseTargetReviewListCreateView):
    url_kwarg = "job_id"

    def get_queryset(self):
        return selectors.get_job_reviews(self.get_target_id())

    def create_review(self, *, reviewer, target_id, rating, comment):
        return ReviewService.create_job_review(
            reviewer=reviewer, job_id=target_id, rating=rating, comment=comment
        )


class ServiceReviewListCreateView(_BaseTargetReviewListCreateView):
    url_kwarg = "service_id"

    def get_queryset(self):
        return selectors.get_service_reviews(self.get_target_id())

    def create_review(self, *, reviewer, target_id, rating, comment):
        return ReviewService.create_service_review(
            reviewer=reviewer,
            service_id=target_id,
            rating=rating,
            comment=comment,
        )


class JobReviewSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, job_id):
        return Response(selectors.get_job_review_stats(job_id))


class ServiceReviewSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, service_id):
        return Response(selectors.get_service_review_stats(service_id))
