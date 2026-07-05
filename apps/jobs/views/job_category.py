from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from ..models import JobCategory
from ..serializers.job_category import JobCategorySerializer


@extend_schema(tags=["Jobs/Category"])
class JobCategoryViewSet(viewsets.ModelViewSet):
    queryset = JobCategory.objects.filter(deleted_at__isnull=True)
    serializer_class = JobCategorySerializer
    pagination_class = None
