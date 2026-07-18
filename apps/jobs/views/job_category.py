from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from apps.users.permissions import IsAdminOrReadOnly

from ..models import JobCategory
from ..serializers.job_category import JobCategorySerializer


@extend_schema(tags=["Jobs/Category"])
class JobCategoryViewSet(viewsets.ModelViewSet):
    queryset = JobCategory.objects.filter(deleted_at__isnull=True)
    serializer_class = JobCategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
