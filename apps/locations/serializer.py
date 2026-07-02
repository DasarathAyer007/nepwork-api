from django.contrib.gis.geos import Point
from rest_framework import serializers

from apps.locations.services import LocationService

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    point = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            "point",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "label",
        )

    def get_point(self, obj):
        if obj.point is None:
            return None
        return {
            "lat": obj.point.y,
            "lng": obj.point.x,
        }

    def to_representation(self, instance):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # decide access level
        is_owner = (
            user and user.is_authenticated and user.location_id == instance.id
        )

        if is_owner:
            return self._filter_by_level(
                instance, Location.VisibilityLevel.EXACT
            )

        return self._filter_by_level(instance, instance.visibility_level)

    def _filter_by_level(self, obj, level):
        if level == Location.VisibilityLevel.PRIVATE:
            return None

        if level == Location.VisibilityLevel.HIDDEN:
            return {"label": obj.label, "type": "hidden"}

        if level == Location.VisibilityLevel.COUNTRY:
            return {"country": obj.country, "type": "country"}

        if level == Location.VisibilityLevel.STATE:
            return {
                "country": obj.country,
                "state": obj.state,
                "type": "state",
            }

        if level == Location.VisibilityLevel.CITY:
            return {
                "country": obj.country,
                "state": obj.state,
                "city": obj.city,
                "type": "city",
            }

        if level == Location.VisibilityLevel.AREA:
            return {
                "country": obj.country,
                "state": obj.state,
                "city": obj.city,
                "postal_code": obj.postal_code,
                "type": "area",
            }

        if level == Location.VisibilityLevel.STREET:
            return {
                "address": obj.address,
                "country": obj.country,
                "city": obj.city,
                "state": obj.state,
                "postal_code": obj.postal_code,
                "type": "street",
            }

        if level == Location.VisibilityLevel.EXACT:
            return {
                "address": obj.address,
                "city": obj.city,
                "state": obj.state,
                "country": obj.country,
                "postal_code": obj.postal_code,
                "point": {
                    "lat": obj.point.y,
                    "lng": obj.point.x,
                },
                "type": "exact",
            }

        return None


class LocationReadSerializer(serializers.ModelSerializer):
    point = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = (
            "point",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "label",
        )

    def get_point(self, obj):
        if obj.point is None:
            return None
        return {
            "lat": obj.point.y,
            "lng": obj.point.x,
        }


class LocationWriteSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(write_only=True, min_value=-90, max_value=90)
    lng = serializers.FloatField(write_only=True, min_value=-180, max_value=180)

    class Meta:
        model = Location
        fields = [
            "lat",
            "lng",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "label",
            "visibility_level",
        ]
        extra_kwargs = {
            # These come from reverse geocoding, so not required from the client.
            # address is an exception: the client may override the geocoded value.
            "city": {"required": False},
            "state": {"required": False},
            "country": {"required": False},
            "postal_code": {"required": False},
        }

    def create(self, validated_data):
        lat = validated_data.pop("lat")
        lng = validated_data.pop("lng")

        geo_data = LocationService.reverse_geocode(lat, lng)

        return Location.objects.create(
            point=Point(lng, lat, srid=4326),
            # Geocoded values are the fallback; client-supplied values win.
            city=validated_data.get("city") or geo_data.get("city", ""),
            state=validated_data.get("state") or geo_data.get("state", ""),
            country=validated_data.get("country")
            or geo_data.get("country", ""),
            postal_code=validated_data.get("postal_code")
            or geo_data.get("postal_code", ""),
            address=validated_data.get("address")
            or geo_data.get("address", ""),
            label=validated_data.get("label", ""),
            visibility_level=validated_data.get(
                "visibility_level", Location.VisibilityLevel.CITY
            ),
        )

    def update(self, instance, validated_data):
        lat = validated_data.pop("lat", None)
        lng = validated_data.pop("lng", None)

        # Only update point and reverse geocode if coordinates changed
        if lat is not None and lng is not None:
            instance.point = Point(lng, lat, srid=4326)
            geo_data = LocationService.reverse_geocode(lat, lng)
        else:
            geo_data = {}

        instance.city = validated_data.get("city") or geo_data.get(
            "city", instance.city
        )
        instance.state = validated_data.get("state") or geo_data.get(
            "state", instance.state
        )
        instance.country = validated_data.get("country") or geo_data.get(
            "country", instance.country
        )
        instance.postal_code = validated_data.get(
            "postal_code"
        ) or geo_data.get("postal_code", instance.postal_code)
        instance.address = validated_data.get("address") or geo_data.get(
            "address", instance.address
        )
        instance.label = validated_data.get("label", instance.label)
        instance.visibility_level = validated_data.get(
            "visibility_level",
            instance.visibility_level,
        )

        instance.save()

        return instance
