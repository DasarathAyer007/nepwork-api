import random
import threading
import time

from django.contrib.gis.geos import Point
from factory.declarations import LazyAttribute, LazyFunction
from factory.django import DjangoModelFactory
from factory.faker import Faker
from faker import Faker as FakerGenerator

from ..models import Location
from ..services import LocationService

fake = FakerGenerator()
# ruff: noqa: S311

# Dhangadhi, Kailali -- most seeded locations should cluster around here
# since that's where this app's users are concentrated.
DHANGADHI_LAT = 28.6833
DHANGADHI_LON = 80.6000

# Rough bounding box covering all of Nepal, used for the occasional
# location scattered elsewhere in the country for variety.
NEPAL_LAT_RANGE = (26.35, 30.45)
NEPAL_LON_RANGE = (80.05, 88.20)

# The reverse-geocoding API is rate limited to 5 requests/second.
REVERSE_GEOCODE_RATE_LIMIT = 4


class _RateLimiter:
    """Blocks callers as needed so calls never exceed `max_per_second`.

    Shared across every LocationFactory call (factory_boy runs create_batch
    serially, but this stays correct even if that ever changes).
    """

    def __init__(self, max_per_second: int):
        self._min_interval = 1 / max_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


_rate_limiter = _RateLimiter(REVERSE_GEOCODE_RATE_LIMIT)


def _random_point() -> tuple[float, float]:
    """~80% of locations land within ~30km of Dhangadhi; the rest are
    scattered anywhere in Nepal so seed data isn't 100% Kailali."""
    if random.random() < 0.7:
        lat = DHANGADHI_LAT + random.uniform(-0.3, 0.3)
        lon = DHANGADHI_LON + random.uniform(-0.3, 0.3)
    else:
        lat = random.uniform(*NEPAL_LAT_RANGE)
        lon = random.uniform(*NEPAL_LON_RANGE)
    return lat, lon


def _reverse_geocode(lat: float, lon: float) -> dict:
    _rate_limiter.wait()
    return LocationService.reverse_geocode(lat, lon)


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location
        exclude = ("seed_point", "geocode_result")

    seed_point = LazyFunction(_random_point)

    geocode_result = LazyAttribute(
        lambda o: _reverse_geocode(o.seed_point[0], o.seed_point[1])
    )

    # Point stores (lon, lat), same order the model already expected.
    point = LazyAttribute(
        lambda o: Point(o.seed_point[1], o.seed_point[0], srid=4326)
    )

    address = LazyAttribute(
        lambda o: (
            o.geocode_result.get("address")
            or f"Ward No. {random.randint(1, 32)}, {fake.street_name()}, Dhangadhi"
        )
    )
    city = LazyAttribute(lambda o: o.geocode_result.get("city") or "Dhangadhi")
    state = LazyAttribute(
        lambda o: o.geocode_result.get("state") or "Sudurpashchim Province"
    )
    country = LazyAttribute(
        lambda o: o.geocode_result.get("country") or "Nepal"
    )
    postal_code = LazyAttribute(
        lambda o: o.geocode_result.get("postal_code") or "10900"
    )

    label = Faker(
        "random_element",
        elements=[
            "Home",
            "Office",
            "Client",
            "Warehouse",
            "Store",
        ],
    )

    visibility_level = Faker(
        "random_element",
        elements=Location.VisibilityLevel.values,
    )
