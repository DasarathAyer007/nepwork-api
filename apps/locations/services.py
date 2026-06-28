# services.py
import logging

import requests

logger = logging.getLogger(__name__)


class LocationService:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
    TIMEOUT = 20  # seconds

    @staticmethod
    def reverse_geocode(lat: float, lng: float) -> dict:
        params = {
            "format": "json",
            "lat": lat,
            "lon": lng,
            "addressdetails": 1,
        }

        HEADERS = {
            "User-Agent": "NepWork/1.0",
            "Accept": "application/json",
        }

        try:
            response = requests.get(
                LocationService.NOMINATIM_URL,
                params=params,
                headers=HEADERS,
                timeout=LocationService.TIMEOUT,
            )
            print(
                f"Reverse geocode response: {response.text}"
            )  # Debugging line
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            logger.warning(
                "Nominatim reverse geocode timed out for (%s, %s)", lat, lng
            )
            return {}
        except requests.RequestException as e:
            logger.error(
                "Nominatim reverse geocode failed for (%s, %s): %s", lat, lng, e
            )
            return {}

        address = data.get("address", {})

        return {
            "city": address.get("city")
            or address.get("town")
            or address.get("village")
            or "",
            "state": address.get("state", ""),
            "country": address.get("country", ""),
            "postal_code": address.get("postcode", ""),
            "address": data.get("display_name", ""),
        }
