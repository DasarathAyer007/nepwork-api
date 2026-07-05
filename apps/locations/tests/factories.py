from random import uniform

from django.contrib.gis.geos import Point
from factory.declarations import LazyFunction
from factory.django import DjangoModelFactory
from factory.faker import Faker
from faker import Faker as FakerGenerator

from ..models import Location

fake = FakerGenerator()
# ruff: noqa: S311


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    # point = LazyFunction(
    #     lambda: Point(
    #         float(fake.longitude()),
    #         float(fake.latitude()),
    #         srid=4326,
    #     )
    # )

    # nepal
    # point = LazyFunction(
    # lambda: Point(
    #     float(uniform(80.0, 88.2)),   # longitude
    #     float(uniform(26.3, 30.5)),   # latitude
    #     srid=4326,
    # )
    # )

    # dhangadhi
    point = LazyFunction(
        lambda: Point(
            float(uniform(80.55, 80.75)),  # longitude
            float(uniform(28.55, 28.75)),  # latitude
            srid=4326,
        )
    )
    address = Faker("street_address")
    city = Faker("city")
    state = Faker("state")
    country = Faker("country")
    postal_code = Faker("postcode")

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
