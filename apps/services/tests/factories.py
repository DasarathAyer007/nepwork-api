import random
from typing import cast

from factory.declarations import (
    Iterator,
    LazyFunction,
    SubFactory,
)
from factory.django import DjangoModelFactory
from factory.faker import Faker
from factory.helpers import post_generation

from apps.locations.tests.factories import LocationFactory
from apps.services.models import Service
from apps.services.models.service_category import ServiceCategory
from apps.skill.models import Skill
from apps.users.models.user import User

# ruff: noqa: S311
SERVICE_TITLES = [
    "House Cleaning",
    "Deep Cleaning",
    "Bathroom Plumbing",
    "Kitchen Plumbing",
    "Electrical Repair",
    "Ceiling Fan Installation",
    "AC Installation",
    "AC Repair",
    "Laptop Repair",
    "Computer Setup",
    "Mobile Screen Replacement",
    "Car Wash",
    "Garden Maintenance",
    "Interior Painting",
    "Roof Leak Repair",
    "Furniture Assembly",
    "Home Moving Service",
    "Pest Control",
    "TV Wall Mount Installation",
    "Water Heater Repair",
]

SERVICE_SKILLS_MAP = {
    "AC Repair": ["repair", "installation", "cooling"],
    "Plumbing Fix": ["repair", "plumbing", "maintenance"],
    "House Cleaning": ["cleaning", "sanitization", "maintenance"],
    "Electrical Work": ["wiring", "repair", "installation"],
    "Laptop Repair": ["repair", "diagnostics", "hardware"],
}


class ServiceCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ServiceCategory
        django_get_or_create = ("name",)

    name = Iterator(
        [
            "Plumbing",
            "Electrical",
            "Cleaning",
            "Painting",
            "Carpentry",
            "HVAC",
            "Appliance Repair",
            "Pest Control",
            "Gardening",
            "Moving",
        ]
    )

    description = Faker("sentence", nb_words=10)

    icon = Iterator(
        [
            "plumbing",
            "bolt",
            "cleaning_services",
            "format_paint",
            "carpenter",
            "ac_unit",
            "home_repair_service",
            "pest_control",
            "yard",
            "local_shipping",
        ]
    )

    is_active = Faker("boolean", chance_of_getting_true=95)


class ServiceFactory(DjangoModelFactory):
    class Meta:
        model = Service

    title = Faker("random_element", elements=SERVICE_TITLES)

    description = Faker("paragraph", nb_sentences=4)

    user = LazyFunction(lambda: random.choice(list(User.objects.all())))

    category = LazyFunction(
        lambda: random.choice(list(ServiceCategory.objects.all()))
    )

    location = SubFactory(LocationFactory)

    availability_status = LazyFunction(
        lambda: random.choices(
            [
                Service.AvailabilityStatus.AVAILABLE,
                Service.AvailabilityStatus.ON_BREAK,
                Service.AvailabilityStatus.UNAVAILABLE,
                Service.AvailabilityStatus.HOLIDAY,
            ],
            weights=[70, 15, 10, 5],
            k=1,
        )[0]
    )  #

    price_type = Faker(
        "random_element",
        elements=Service.PriceType.values,
    )

    status = LazyFunction(
        lambda: random.choices(
            [
                Service.ServiceStatus.ACTIVE,
                Service.ServiceStatus.DRAFT,
                Service.ServiceStatus.PAUSED,
                Service.ServiceStatus.CLOSED,
            ],
            weights=[90, 5, 2, 3],
            k=1,
        )[0]
    )

    price = Faker(
        "pydecimal",
        left_digits=3,
        right_digits=2,
        positive=True,
    )

    currency = "NPR"

    radius_km = Faker(
        "random_int",
        min=1,
        max=50,
    )

    available_from = Faker("time_object")

    available_to = Faker("time_object")

    @post_generation
    def skills(self, create, extracted, **kwargs):
        if not create:
            return

        skill_names = []

        title = cast(str, self.title)
        skill_names = extracted or SERVICE_SKILLS_MAP.get(title, [])

        skill_objs = []

        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip().lower())
            skill_objs.append(skill)

        self.skills.set(skill_objs)
