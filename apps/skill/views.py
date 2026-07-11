from django.db.models import Count, F
from drf_spectacular.utils import extend_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView

from apps.skill.models import Skill
from apps.skill.serializer import SkillUsageSerializer


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
class SkillListView(ListAPIView):
    serializer_class = SkillUsageSerializer

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ["name"]

    ordering_fields = [
        "name",
        "personal_count",
        "job_count",
        "service_count",
        "total_count",
    ]

    pagination_class = None

    ordering = ["name"]

    def get_queryset(self):
        return annotated_skill_queryset()


@extend_schema(tags=["Skills"])
class PopularSkillsView(ListAPIView):
    """Most-used skills across jobs, services and personal profiles.

    Supports a `type` query param (`job`, `service`, `personal`, `all`) to
    scope popularity to a single usage category instead of the combined
    total. Defaults to `all` when omitted.
    """

    serializer_class = SkillUsageSerializer

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
