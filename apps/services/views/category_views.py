# services/category_views.py
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import ServiceCategory
from ..selectors.category_selectors import get_popular_categories
from ..serializers import CategorySerializer, PopularCategorySerializer


@extend_schema(tags=["Services/Category"])
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    pagination_class = None

    DEFAULT_LIMIT = 10
    MAX_LIMIT = 50

    @extend_schema(responses=PopularCategorySerializer(many=True))
    @action(detail=False, methods=["get"], url_path="popular")
    def popular(self, request):
        qs = get_popular_categories(limit=self._get_limit(request))
        serializer = PopularCategorySerializer(qs, many=True)
        return Response(serializer.data)

    def _get_limit(self, request):
        try:
            limit = int(request.query_params.get("limit", self.DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = self.DEFAULT_LIMIT
        return max(1, min(limit, self.MAX_LIMIT))
