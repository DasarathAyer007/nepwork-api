from rest_framework.viewsets import ModelViewSet

from apps.locations.models.locations import Location
from apps.locations.serializers import (
    LocationSerializer,
    LocationWriteSerializer,
)


class LocationViewSet(ModelViewSet):
    queryset = Location.objects.all()
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return LocationWriteSerializer
        return LocationSerializer
