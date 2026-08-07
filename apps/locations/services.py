import logging

import requests
from django.db.models import Q

from config.geo_coding import (
    REVERSE_GEOCODING_API_KEY,
    REVERSE_GEOCODING_API_URL,
)

from .models import Location

logger = logging.getLogger(__name__)


class LocationService:
    TIMEOUT = 20  # seconds

    @staticmethod
    def reverse_geocode(lat: float, lng: float) -> dict:
        url = str(REVERSE_GEOCODING_API_URL)

        params = {
            "apiKey": REVERSE_GEOCODING_API_KEY,
            "lat": lat,
            "lon": lng,
        }

        headers = {
            "User-Agent": "NepWork/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=LocationService.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            print("Reverse geocode response:", data)  # Debugging line

        except requests.Timeout:
            logger.warning(
                "Reverse geocode timed out for (%s, %s)",
                lat,
                lng,
            )
            return {}

        except requests.RequestException as e:
            logger.error(
                "Reverse geocode failed for (%s, %s): %s",
                lat,
                lng,
                e,
            )
            return {}

        features = data.get("features", [])
        if not features:
            return {}

        properties = features[0].get("properties", {})

        return {
            "city": (
                properties.get("city")
                or properties.get("town")
                or properties.get("village")
                or ""
            ),
            "state": properties.get("state", ""),
            "country": properties.get("country", ""),
            "country_code": properties.get("country_code", "").upper(),
            "postal_code": properties.get("postcode", ""),
            "district": properties.get("district", ""),
            "suburb": properties.get("suburb", ""),
            "county": properties.get("county", ""),
            "street": properties.get("street", ""),
            "house_number": properties.get("housenumber", ""),
            "address": properties.get("formatted", ""),
            "latitude": properties.get("lat"),
            "longitude": properties.get("lon"),
        }


class SearchService:
    @staticmethod
    def get_search_suggestions(query: str) -> list:
        if not query:
            return []
        qs = (
            Location.objects.filter(
                Q(city__icontains=query)
                | Q(state__icontains=query)
                | Q(country__icontains=query)
                | Q(postal_code__icontains=query)
                | Q(address__icontains=query)
            )
            .values("id", "city", "state", "address")
            .distinct()[:15]
        )

        return list(qs)
