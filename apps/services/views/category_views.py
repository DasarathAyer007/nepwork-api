# services/category_views.py
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from ..models import ServiceCategory
from ..serializers import CategorySerializer


@extend_schema(tags=["Services/Category"])
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = CategorySerializer
