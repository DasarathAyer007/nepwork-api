from django.db.models import Count, F
from drf_spectacular.utils import extend_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from apps.skill.models import Skill
from apps.skill.serializer import SkillSerializer, SkillUsageSerializer
from apps.users.permissions import IsAdminOrReadOnly
from apps.utils.pagination import CustomPageNumberPagination


def annotated_skill_queryset():
    """Skill queryset annotated with usage counts across the platform."""
    return Skill.objects.annotate(
        personal_count=Count("personalprofile", distinct=True),
        job_count=Count("job", distinct=True),
        service_count=Count("service", distinct=True),
    ).annotate(
        total_count=(F("personal_count") + F("job_count") + F("service_count"))
    )


@extend_schema(tags=["Skills"])
class SkillListView(ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly("skills")]

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ["name"]

    ordering_fields = [
        "id",
        "name",
        "personal_count",
        "job_count",
        "service_count",
        "total_count",
    ]

    pagination_class = CustomPageNumberPagination

    ordering = ["name"]

    SORTBY_MAP = {
        "newest": ["-id"],
        "popular": ["-total_count", "name"],
        "popular:job": ["-job_count", "name"],
        "popular:service": ["-service_count", "name"],
        "popular:user": ["-personal_count", "name"],
    }

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SkillSerializer
        return SkillUsageSerializer

    def get_queryset(self):
        return annotated_skill_queryset()

    def filter_queryset(self, queryset):
        sortby = self.request.query_params.get("sortby")
        if sortby and sortby in self.SORTBY_MAP:
            # Filter by search fields first
            queryset = SearchFilter().filter_queryset(
                self.request, queryset, self
            )
            return queryset.order_by(*self.SORTBY_MAP[sortby])
        return super().filter_queryset(queryset)

    def paginate_queryset(self, queryset):
        if self.request.query_params.get("paginate") == "false":
            return None
        return super().paginate_queryset(queryset)


@extend_schema(tags=["Skills"])
class SkillDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrReadOnly("skills")]

    def get_queryset(self):
        if self.request.method == "GET":
            return annotated_skill_queryset()
        return Skill.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return SkillUsageSerializer
        return SkillSerializer


@extend_schema(tags=["Skills"])
class PopularSkillsView(ListAPIView):
    """Most-used skills across jobs, services and personal profiles.

    Supports a `type` query param (`job`, `service`, `personal`, `all`) to
    scope popularity to a single usage category instead of the combined
    total. Defaults to `all` when omitted.
    """

    serializer_class = SkillUsageSerializer

    # permission_classes = [AllowAny]

    filter_backends = [SearchFilter]

    search_fields = ["name"]

    pagination_class = None

    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    COUNT_FIELD_BY_TYPE = {
        "job": "job_count",
        "service": "service_count",
        "personal": "personal_count",
        "all": "total_count",
    }

    def get_queryset(self):
        count_field = self._get_count_field()
        qs = (
            annotated_skill_queryset()
            .filter(**{f"{count_field}__gt": 0})
            .order_by(f"-{count_field}", "name")
        )
        return qs[: self._get_limit()]

    def _get_count_field(self):
        skill_type = (self.request.query_params.get("type") or "all").lower()
        return self.COUNT_FIELD_BY_TYPE.get(skill_type, "total_count")

    def _get_limit(self):
        try:
            limit = int(
                self.request.query_params.get("limit", self.DEFAULT_LIMIT)
            )
        except (TypeError, ValueError):
            limit = self.DEFAULT_LIMIT
        return max(1, min(limit, self.MAX_LIMIT))
