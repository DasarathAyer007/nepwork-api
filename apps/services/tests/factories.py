import datetime
import random
from typing import Any, cast

import factory
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

_category_cache: dict[str, ServiceCategory] = {}


def _get_category(name: str) -> ServiceCategory:
    if name not in _category_cache:
        _category_cache[name], _ = ServiceCategory.objects.get_or_create(
            name=name
        )
    return _category_cache[name]


def _random_provider_user_id():
    """Pick a random provider (personal/organization) user id.

    Services are always owned by a real seeded user, so this deliberately
    raises instead of letting `random.choice` crash with an opaque
    IndexError on an empty queryset -- run the user seed step first.
    """
    ids = list(
        User.objects.exclude(account_type=User.AccountType.ADMIN).values_list(
            "id", flat=True
        )
    )
    if not ids:
        msg = (
            "No provider users found. Seed users "
            "(e.g. `manage.py seed --users 20`) before seeding services."
        )
        raise RuntimeError(msg)
    return random.choice(ids)


def _random_business_hours():
    """Realistic, ordered working hours (e.g. 07:00-19:00), not fully
    random independent times that could make a service look open 24/7 or
    closed before it opens."""
    start_hour = random.randint(6, 11)
    end_hour = random.randint(start_hour + 2, 20)
    return (
        datetime.time(hour=start_hour, minute=random.choice([0, 15, 30, 45])),
        datetime.time(hour=end_hour, minute=random.choice([0, 15, 30, 45])),
    )


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
        exclude = ("seed_entry", "business_hours")

    seed_entry = LazyFunction(lambda: random.choice(SERVICES))

    # kept random on purpose, no Iterator here
    title = LazyAttribute(lambda o: o.seed_entry["title"])

    description = LazyAttribute(lambda o: o.seed_entry["description"])

    user_id = LazyFunction(_random_provider_user_id)

    category = LazyAttribute(lambda o: _get_category(o.seed_entry["category"]))

    location = SubFactory(LocationFactory)

    thumbnail = factory.django.ImageField(color="lightgray")

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

    # A paused/closed/draft service can't realistically be "available" -
    # tie availability to status instead of rolling two unrelated dice.
    availability_status = LazyAttribute(
        lambda o: (
            random.choices(
                [
                    Service.AvailabilityStatus.AVAILABLE,
                    Service.AvailabilityStatus.ON_BREAK,
                    Service.AvailabilityStatus.HOLIDAY,
                ],
                weights=[90, 6, 4],
                k=1,
            )[0]
            if o.status == Service.ServiceStatus.ACTIVE
            else Service.AvailabilityStatus.UNAVAILABLE
        )
    )

    price_type = Faker(
        "random_element",
        elements=Service.PriceType.values,
    )

    # Hourly rates and fixed project quotes live on very different scales;
    # a flat 0-999.99 range made hourly gigs look absurdly expensive.
    price = LazyAttribute(
        lambda o: round(
            random.uniform(300, 2500)
            if o.price_type == Service.PriceType.HOURLY
            else random.uniform(1000, 50000),
            2,
        )
    )

    currency = "NPR"

    radius_km = Faker(
        "random_int",
        min=1,
        max=50,
    )

    business_hours = LazyFunction(_random_business_hours)

    available_from = LazyAttribute(lambda o: o.business_hours[0])

    available_to = LazyAttribute(lambda o: o.business_hours[1])

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
