from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
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

    def to_representation(self, instance):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # decide access level
        is_owner = (
            user
            and user.is_authenticated
            and hasattr(user, "location")
            and user.location_id == instance.id
        )

        level = "full" if is_owner else instance.visibility_level

        return self._filter_by_level(instance, level)

    def _filter_by_level(self, obj, level):
        if level == Location.VisibilityLevel.PRIVATE:
            return None

        if level == Location.VisibilityLevel.HIDDEN:
            return {"label": obj.label}

        if level == Location.VisibilityLevel.COUNTRY:
            return {"country": obj.country}

        if level == Location.VisibilityLevel.STATE:
            return {
                "country": obj.country,
                "state": obj.state,
            }

        if level == Location.VisibilityLevel.CITY:
            return {
                "country": obj.country,
                "state": obj.state,
                "city": obj.city,
            }

        if level == Location.VisibilityLevel.AREA:
            return {
                "country": obj.country,
                "state": obj.state,
                "city": obj.city,
                "postal_code": obj.postal_code,
            }

        if level == Location.VisibilityLevel.STREET:
            return {
                "address": obj.address,
                "city": obj.city,
                "state": obj.state,
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
            }

        return None
