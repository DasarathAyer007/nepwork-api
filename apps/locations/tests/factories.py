import random

from django.contrib.gis.geos import Point
from factory.declarations import LazyAttribute, LazyFunction
from factory.django import DjangoModelFactory
from factory.faker import Faker
from faker import Faker as FakerGenerator

from ..models import Location

fake = FakerGenerator()
# ruff: noqa: S311

# Places within Kailali district (Dhangadhi and its surrounding
# municipalities) -- most seeded locations should land here since that's
# where this app's users are concentrated.
KAILALI_PLACES = [
    {
        "city": "Dhangadhi",
        "state": "Sudurpashchim Province",
        "postal_code": "10900",
        "lat": 28.6833,
        "lon": 80.6000,
    },
    {
        "city": "Tikapur",
        "state": "Sudurpashchim Province",
        "postal_code": "10902",
        "lat": 28.5222,
        "lon": 81.1281,
    },
    {
        "city": "Lamki Chuha",
        "state": "Sudurpashchim Province",
        "postal_code": "10901",
        "lat": 28.5722,
        "lon": 80.7161,
    },
    {
        "city": "Godawari, Kailali",
        "state": "Sudurpashchim Province",
        "postal_code": "10900",
        "lat": 28.7167,
        "lon": 80.5833,
    },
    {
        "city": "Ghodaghodi",
        "state": "Sudurpashchim Province",
        "postal_code": "10901",
        "lat": 28.6333,
        "lon": 80.8000,
    },
    {
        "city": "Bhajani",
        "state": "Sudurpashchim Province",
        "postal_code": "10903",
        "lat": 28.5667,
        "lon": 80.8333,
    },
    {
        "city": "Joshipur",
        "state": "Sudurpashchim Province",
        "postal_code": "10901",
        "lat": 28.5833,
        "lon": 80.8667,
    },
    {
        "city": "Janaki Rural Municipality",
        "state": "Sudurpashchim Province",
        "postal_code": "10900",
        "lat": 28.6500,
        "lon": 80.6833,
    },
    {
        "city": "Kailari",
        "state": "Sudurpashchim Province",
        "postal_code": "10900",
        "lat": 28.6333,
        "lon": 80.5000,
    },
    {
        "city": "Mohanyal",
        "state": "Sudurpashchim Province",
        "postal_code": "10900",
        "lat": 28.7500,
        "lon": 80.5333,
    },
]

# A handful of other major Nepali cities for occasional variety, so not
# every single location is in Kailali.
OTHER_NEPAL_CITIES = [
    {
        "city": "Kathmandu",
        "state": "Bagmati Province",
        "postal_code": "44600",
        "lat": 27.7172,
        "lon": 85.3240,
    },
    {
        "city": "Lalitpur",
        "state": "Bagmati Province",
        "postal_code": "44700",
        "lat": 27.6644,
        "lon": 85.3188,
    },
    {
        "city": "Bhaktapur",
        "state": "Bagmati Province",
        "postal_code": "44800",
        "lat": 27.6710,
        "lon": 85.4298,
    },
    {
        "city": "Pokhara",
        "state": "Gandaki Province",
        "postal_code": "33700",
        "lat": 28.2096,
        "lon": 83.9856,
    },
    {
        "city": "Biratnagar",
        "state": "Koshi Province",
        "postal_code": "56613",
        "lat": 26.4525,
        "lon": 87.2718,
    },
    {
        "city": "Birgunj",
        "state": "Madhesh Province",
        "postal_code": "44300",
        "lat": 27.0104,
        "lon": 84.8821,
    },
    {
        "city": "Dharan",
        "state": "Koshi Province",
        "postal_code": "56700",
        "lat": 26.8065,
        "lon": 87.2846,
    },
    {
        "city": "Bharatpur",
        "state": "Bagmati Province",
        "postal_code": "44200",
        "lat": 27.6766,
        "lon": 84.4340,
    },
    {
        "city": "Janakpur",
        "state": "Madhesh Province",
        "postal_code": "45600",
        "lat": 26.7288,
        "lon": 85.9266,
    },
    {
        "city": "Hetauda",
        "state": "Bagmati Province",
        "postal_code": "44107",
        "lat": 27.4287,
        "lon": 85.0324,
    },
    {
        "city": "Nepalgunj",
        "state": "Lumbini Province",
        "postal_code": "21900",
        "lat": 28.0500,
        "lon": 81.6167,
    },
    {
        "city": "Itahari",
        "state": "Koshi Province",
        "postal_code": "56705",
        "lat": 26.6650,
        "lon": 87.2750,
    },
    {
        "city": "Butwal",
        "state": "Lumbini Province",
        "postal_code": "32907",
        "lat": 27.7000,
        "lon": 83.4486,
    },
    {
        "city": "Ghorahi",
        "state": "Lumbini Province",
        "postal_code": "22400",
        "lat": 28.0333,
        "lon": 82.4833,
    },
]

# Real Nepali places with their province and approximate coordinates, so a
# generated location has a city/state/point that all agree with each other
# instead of e.g. a random US-sounding Faker city paired with country="Nepal".
NEPAL_CITIES = KAILALI_PLACES + OTHER_NEPAL_CITIES


def _random_seed_city():
    # ~80% of locations fall within Kailali district (Dhangadhi area).
    pool = KAILALI_PLACES if random.random() < 0.8 else OTHER_NEPAL_CITIES
    return random.choice(pool)


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location
        exclude = ("seed_city",)

    seed_city = LazyFunction(_random_seed_city)

    # Small jitter around the city center keeps points spread out without
    # drifting into a different city or, worse, a different country.
    point = LazyAttribute(
        lambda o: Point(
            o.seed_city["lon"] + random.uniform(-0.05, 0.05),
            o.seed_city["lat"] + random.uniform(-0.05, 0.05),
            srid=4326,
        )
    )

    address = LazyAttribute(
        lambda o: (
            f"Ward No. {random.randint(1, 32)}, {fake.street_name()}, "
            f"{o.seed_city['city']}"
        )
    )
    city = LazyAttribute(lambda o: o.seed_city["city"])
    state = LazyAttribute(lambda o: o.seed_city["state"])
    country = "Nepal"
    postal_code = LazyAttribute(lambda o: o.seed_city["postal_code"])

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
