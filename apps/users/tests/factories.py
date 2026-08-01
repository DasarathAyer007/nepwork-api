import datetime
import random

import factory
from factory.declarations import (
    Iterator,
    LazyAttribute,
    LazyFunction,
    PostGenerationMethodCall,
)
from factory.django import DjangoModelFactory
from factory.faker import Faker
from factory.helpers import post_generation
from faker import Faker as FakerProvider

from apps.skill.models import Skill
from apps.skill.tests.factories import SkillFactory
from apps.users.models import User
from apps.utils.json_loader import load_json

from ..models import (
    OrganizationProfile,
    PersonalProfile,
)

# ruff: noqa: S311, SIM102
data = load_json("apps/users/tests/seed_data.json")
USERS = data["users"]
INDUSTRIES = data.get("industries", ["Technology"])

fake = FakerProvider()


def _parse_date(value):
    if not value:
        return None
    return datetime.date.fromisoformat(value)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)
        exclude = ("seed_entry",)

    # Cycles through every seed entry before repeating, so batches up to
    # len(USERS) never collide on username/email.
    seed_entry = Iterator(USERS)

    full_name = LazyAttribute(lambda o: o.seed_entry["full_name"])

    username = LazyAttribute(lambda o: o.seed_entry["username"])

    email = LazyAttribute(lambda o: o.seed_entry["email"])

    password = PostGenerationMethodCall(
        "set_password",
        "test",
    )

    phone_number = LazyAttribute(lambda o: o.seed_entry.get("phone_number", ""))

    social_links = LazyAttribute(lambda o: o.seed_entry.get("social_links", {}))

    account_type = LazyAttribute(
        lambda o: (
            User.AccountType.PERSONAL
            if o.seed_entry.get("type") == "individual"
            else User.AccountType.ORGANIZATION
        )
    )

    status = Faker(
        "random_element",
        elements=User.Status.values,
    )

    bio = LazyAttribute(
        lambda o: o.seed_entry.get("bio") or fake.paragraph(nb_sentences=3)
    )

    profile_visibility = Faker(
        "random_element",
        elements=User.ProfileVisibility.values,
    )

    is_locked = Faker(
        "boolean",
        chance_of_getting_true=5,
    )

    failed_login_attempts = LazyAttribute(
        lambda obj: 0 if not obj.is_locked else 3
    )

    two_factor_enabled = Faker(
        "boolean",
        chance_of_getting_true=30,
    )

    location = None

    @post_generation
    def create_profile(self, create, extracted, **kwargs):
        if not create:
            return

        # Find the matching seed entry for the generated user.
        seed_entry = next(
            (u for u in USERS if u["username"] == self.username), None
        )
        seed_entry = seed_entry or {}

        if self.account_type == User.AccountType.PERSONAL:
            if not PersonalProfile.objects.filter(user=self).exists():
                interests = seed_entry.get("interests", [])
                kwargs = {
                    "user": self,
                    "interests": interests,
                    "skills": seed_entry.get("skills", interests),
                }
                if seed_entry.get("gender"):
                    kwargs["gender"] = seed_entry["gender"]
                date_of_birth = _parse_date(seed_entry.get("date_of_birth"))
                if date_of_birth:
                    kwargs["date_of_birth"] = date_of_birth
                PersonalProfileFactory(**kwargs)

        elif self.account_type == User.AccountType.ORGANIZATION:
            if not OrganizationProfile.objects.filter(user=self).exists():
                industries = seed_entry.get("industries", [])
                kwargs = {
                    "user": self,
                    "industry": (
                        industries[0]
                        if industries
                        else random.choice(INDUSTRIES)
                    ),
                }
                for field in (
                    "employees_count",
                    "address",
                    "tax_id",
                    "is_verified",
                ):
                    if seed_entry.get(field) is not None:
                        kwargs[field] = seed_entry[field]
                founded_at = _parse_date(seed_entry.get("founded_at"))
                if founded_at:
                    kwargs["founded_at"] = founded_at
                OrganizationProfileFactory(**kwargs)


class PersonalProfileFactory(DjangoModelFactory):
    class Meta:
        model = PersonalProfile

    user = None  # IMPORTANT: set by UserFactory

    date_of_birth = Faker(
        "date_of_birth",
        minimum_age=18,
        maximum_age=60,
    )

    gender = Faker(
        "random_element",
        elements=[c[0] for c in PersonalProfile.Gender.choices],
    )

    interests = LazyFunction(list)

    @post_generation
    def skills(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            skill_objs = []
            for item in extracted:
                skill, _ = Skill.objects.get_or_create(
                    name=str(item).strip().lower()
                )
                skill_objs.append(skill)
        else:
            skill_objs = SkillFactory.create_batch(2)

        self.skills.set(skill_objs)


class OrganizationProfileFactory(DjangoModelFactory):
    class Meta:
        model = OrganizationProfile

    user = None  # IMPORTANT: set by UserFactory

    industry = LazyAttribute(lambda o: random.choice(INDUSTRIES))

    logo = factory.django.ImageField(color="blue")

    employees_count = Faker("random_int", min=1, max=500)

    founded_at = Faker("date_between", start_date="-30y", end_date="-1y")

    address = Faker("address")

    tax_id = Faker("bothify", text="TAX-##########")

    is_verified = Faker("boolean", chance_of_getting_true=40)
