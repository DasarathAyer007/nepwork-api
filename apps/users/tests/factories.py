import random

import factory
from factory.declarations import (
    Dict,
    LazyAttribute,
    LazyFunction,
    PostGenerationMethodCall,
)
from factory.django import DjangoModelFactory
from factory.faker import Faker
from factory.helpers import post_generation

from apps.skill.models import Skill
from apps.skill.tests.factories import SkillFactory
from apps.users.models import User

from ..models import OrganizationProfile, PersonalProfile


# ruff: noqa: S311
class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    full_name = Faker("name")

    username = Faker("user_name", unique=True)

    email = Faker("email")

    password = PostGenerationMethodCall(
        "set_password",
        "test",
    )

    phone_number = Faker("phone_number")

    account_type = Faker(
        "random_element",
        elements=[
            User.AccountType.PERSONAL,
            User.AccountType.ORGANIZATION,
        ],
    )

    status = Faker(
        "random_element",
        elements=User.Status.values,
    )

    bio = Faker("paragraph", nb_sentences=3)

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

    social_links = Dict(
        {
            "facebook": Faker("url"),
            "instagram": Faker("url"),
            "linkedin": Faker("url"),
        }
    )

    location = None

    @post_generation
    def create_profile(self, create, extracted, **kwargs):
        if not create:
            return

        if self.account_type == User.AccountType.PERSONAL:
            PersonalProfileFactory(user=self)

        elif self.account_type == User.AccountType.ORGANIZATION:
            OrganizationProfileFactory(user=self)


INTERESTS_POOL = [
    "music",
    "sports",
    "technology",
    "travel",
    "gaming",
    "reading",
    "fitness",
    "photography",
    "cooking",
    "movies",
]


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

    interests = LazyFunction(
        lambda: random.sample(INTERESTS_POOL, k=random.randint(2, 5))
    )

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

    user = None

    industry = Faker(
        "random_element", elements=["Technology", "Healthcare", "Finance"]
    )

    logo = factory.django.ImageField(color="blue")

    employees_count = Faker("random_int", min=1, max=500)

    founded_at = Faker("date_between", start_date="-30y", end_date="-1y")

    address = Faker("address")

    tax_id = Faker("bothify", text="TAX-##########")

    is_verified = Faker("boolean", chance_of_getting_true=40)
