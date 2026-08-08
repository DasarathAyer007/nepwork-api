import datetime
import random
from pathlib import Path
from typing import cast

from django.core.files.base import ContentFile
from django.utils.text import slugify
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
from apps.utils.tests.thumbnail_generator import generate_service_thumbnail

data = load_json("apps/services/tests/seed_data.json")
CATEGORIES = data["categories"]
SERVICES = data["services"]

# ruff: noqa: S311

SERVICE_ICONS_DIR = (
    Path(__file__).resolve().parent / "seed_image" / "services_category"
)


def _load_icon_bytes(icon_name: str) -> bytes:
    return (SERVICE_ICONS_DIR / f"{icon_name}.svg").read_bytes()


_category_cache: dict[str, ServiceCategory] = {}


def _get_category(name: str) -> ServiceCategory:
    if name not in _category_cache:
        _category_cache[name], _ = ServiceCategory.objects.get_or_create(
            name=name
        )

    return _category_cache[name]


def _random_provider_user_id():
    """Pick a random provider user id, favoring individual/personal
    accounts (services are mostly offered by individuals)."""

    rows = list(
        User.objects.exclude(account_type=User.AccountType.ADMIN).values_list(
            "id", "account_type"
        )
    )

    if not rows:
        msg = (
            "No provider users found. Seed users "
            "(e.g. `manage.py seed --users 20`) "
            "before seeding services."
        )
        raise RuntimeError(msg)

    personal_ids = [
        user_id
        for user_id, account_type in rows
        if account_type == User.AccountType.PERSONAL
    ]
    other_ids = [
        user_id
        for user_id, account_type in rows
        if account_type != User.AccountType.PERSONAL
    ]

    if personal_ids and other_ids:
        pool = random.choices([personal_ids, other_ids], weights=[90, 10], k=1)[
            0
        ]
    else:
        pool = personal_ids or other_ids

    return random.choice(pool)


def _random_business_hours():
    """Generate realistic ordered working hours."""

    start_hour = random.randint(6, 11)
    end_hour = random.randint(
        start_hour + 2,
        20,
    )

    return (
        datetime.time(
            hour=start_hour,
            minute=random.choice([0, 15, 30, 45]),
        ),
        datetime.time(
            hour=end_hour,
            minute=random.choice([0, 15, 30, 45]),
        ),
    )


class ServiceCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ServiceCategory
        django_get_or_create = ("name",)
        exclude = ("icon_name",)

    name = Iterator([c["name"] for c in CATEGORIES])

    description = Iterator([c["description"] for c in CATEGORIES])

    color = Iterator([c["color"] for c in CATEGORIES])

    is_active = Faker(
        "boolean",
        chance_of_getting_true=95,
    )

    icon_name = Iterator([c["icon"] for c in CATEGORIES])

    # icon = factory.django.FileField(
    #     filename=LazyAttribute(lambda o: f"{o.icon_name}.svg"),
    #     data=LazyAttribute(lambda o: _load_icon_bytes(o.icon_name)),
    # )

    icon = LazyAttribute(
        lambda o: ContentFile(
            _load_icon_bytes(o.icon_name),
            name=f"{o.icon_name}.svg",
        )
    )


class ServiceFactory(DjangoModelFactory):
    class Meta:
        model = Service
        exclude = (
            "seed_entry",
            "business_hours",
        )

    seed_entry = Iterator(SERVICES)

    title = LazyAttribute(lambda o: o.seed_entry["title"])

    description = LazyAttribute(lambda o: o.seed_entry["description"])

    user_id = LazyFunction(_random_provider_user_id)

    category = LazyAttribute(lambda o: _get_category(o.seed_entry["category"]))

    location = SubFactory(LocationFactory)

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

    price = LazyAttribute(
        lambda o: round(
            random.uniform(
                300,
                2500,
            )
            if o.price_type == Service.PriceType.HOURLY
            else random.uniform(
                1000,
                50000,
            ),
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
    def skills(
        self,
        create,
        extracted,
        **kwargs,
    ):
        if not create:
            return

        service = cast(
            Service,
            self,
        )

        title = service.title

        service_data = next(
            (item for item in SERVICES if item["title"] == title),
            None,
        )

        if not service_data:
            return

        skill_names = service_data.get(
            "skills",
            [],
        )

        skill_objs = []

        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip().lower())
            skill_objs.append(skill)

        service.skills.set(skill_objs)

        category = cast(
            ServiceCategory,
            service.category,
        )

        thumbnail = generate_service_thumbnail(
            title=title,
            skills=skill_names[:4],
            color=category.color,
        )

        service.thumbnail.save(
            f"{slugify(title)}.jpg",
            ContentFile(thumbnail),
            save=True,
        )
