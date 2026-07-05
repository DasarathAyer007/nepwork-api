from django.db.models import Count, F
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView

from apps.skill.models import Skill
from apps.skill.serializer import SkillSerializer


class SkillListView(ListAPIView):
    serializer_class = SkillSerializer

    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = ["name"]

    ordering_fields = [
        "name",
        "created_at",
        "personal_count",
        "job_count",
        "service_count",
        "total_count",
    ]

    pagination_class = None

    ordering = ["name"]

    def get_queryset(self):
        return Skill.objects.annotate(
            personal_count=Count("personalprofile", distinct=True),
            job_count=Count("job", distinct=True),
            service_count=Count("service", distinct=True),
        ).annotate(
            total_count=(
                F("personal_count") + F("job_count") + F("service_count")
            )
        )
