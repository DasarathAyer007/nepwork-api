from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from apps.users.permissions import IsAdminOrReadOnly

from .models import SlidingImage
from .serializers import SlidingImageSerializer


@extend_schema(tags=["Admin Panel/Sliding Images"])
class SlidingImageViewSet(viewsets.ModelViewSet):
    queryset = SlidingImage.objects.filter(deleted_at__isnull=True)
    serializer_class = SlidingImageSerializer
    permission_classes = [IsAdminOrReadOnly("sliding_images")]
    pagination_class = None
