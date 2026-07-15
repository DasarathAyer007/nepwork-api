import random
from typing import Any, cast

from factory.declarations import (
    Iterator,
    LazyAttribute,
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
from apps.utils.json_loader import load_json

data = load_json("apps/services/tests/seed_data.json")
categories = data["categories"]
SERVICES = data["services"]

# ruff: noqa: S311


class ServiceCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ServiceCategory
        django_get_or_create = ("name",)

    name = Iterator([c["name"] for c in categories])
    icon = Iterator([c["icon"] for c in categories])
    description = Iterator([c["description"] for c in categories])
    color = Iterator([c["color"] for c in categories])

    is_active = Faker("boolean", chance_of_getting_true=95)


class ServiceFactory(DjangoModelFactory):
    class Meta:
        model = Service
        exclude = ("seed_entry",)

    seed_entry = LazyFunction(lambda: random.choice(SERVICES))

    # kept random on purpose, no Iterator here
    title = LazyAttribute(lambda o: o.seed_entry["title"])

    description = LazyAttribute(lambda o: o.seed_entry["description"])

    user = LazyFunction(lambda: random.choice(list(User.objects.all())))

    category = LazyAttribute(
        lambda o: ServiceCategory.objects.get_or_create(
            name=o.seed_entry["category"]
        )[0]
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
            weights=[90, 4, 4, 2],
            k=1,
        )[0]
    )

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
            weights=[95, 1, 2, 2],
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

        service = next((s for s in SERVICES if s["title"] == self.title), None)

        if not service:
            return

        skill_names = service.get("skills", [])

        skill_objs = []
        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip().lower())
            skill_objs.append(skill)

        cast(Any, self.skills).set(skill_objs)
