from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.locations.models.locations import Location
from apps.locations.serializers import (
    LocationSerializer,
    LocationWriteSerializer,
    ReverseGeocodeQuerySerializer,
)

from .services import LocationService


class LocationViewSet(ModelViewSet):
    queryset = Location.objects.all()
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return LocationWriteSerializer
        return LocationSerializer


@extend_schema(
    parameters=[ReverseGeocodeQuerySerializer],
)
class ReverseGeocodingView(APIView):
    def get(self, request, format=None):
        serializer = ReverseGeocodeQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        lat = serializer.validated_data["lat"]
        lng = serializer.validated_data["lng"]

        location_data = LocationService.reverse_geocode(lat, lng)

        if not location_data:
            return Response(
                {"error": "Unable to retrieve location data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(location_data)
