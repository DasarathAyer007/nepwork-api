from django.contrib.gis.geos import Point
from factory.declarations import LazyFunction
from factory.django import DjangoModelFactory
from factory.faker import Faker
from faker import Faker as FakerGenerator

from ..models import Location

fake = FakerGenerator()


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    point = LazyFunction(
        lambda: Point(
            float(fake.longitude()),
            float(fake.latitude()),
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
