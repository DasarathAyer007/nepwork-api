import random

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

from apps.jobs.models import Job, JobCategory
from apps.locations.tests.factories import LocationFactory
from apps.skill.models import Skill
from apps.users.models import OrganizationProfile, User
from apps.users.tests.factories import UserFactory
from apps.utils.json_loader import load_json

data = load_json("apps/jobs/tests/seed_data.json")
categories = data["categories"]
JOBS = data["jobs"]

# ruff: noqa: S311

_category_cache: dict[str, JobCategory] = {}

# Keeps years-of-experience and salary bands internally consistent instead
# of rolling three unrelated dice (e.g. a "Lead" role paying entry-level
# salary with 1 year of experience required).
_EXPERIENCE_YEARS_RANGE = {
    Job.ExperienceLevel.ENTRY: (0, 2),
    Job.ExperienceLevel.MID: (2, 5),
    Job.ExperienceLevel.SENIOR: (5, 10),
    Job.ExperienceLevel.LEAD: (8, 15),
}

# Rough monthly NPR salary bands by experience level.
_SALARY_RANGE_NPR = {
    Job.ExperienceLevel.ENTRY: (25_000, 45_000),
    Job.ExperienceLevel.MID: (45_000, 80_000),
    Job.ExperienceLevel.SENIOR: (80_000, 150_000),
    Job.ExperienceLevel.LEAD: (150_000, 250_000),
}


def _get_category(name: str) -> JobCategory:
    if name not in _category_cache:
        _category_cache[name], _ = JobCategory.objects.get_or_create(name=name)
    return _category_cache[name]


def _random_poster_user():
    """Pick a random non-admin user to post the job, falling back to
    creating one so standalone `JobFactory()` calls still work without a
    prior user-seeding step."""
    qs = User.objects.exclude(account_type=User.AccountType.ADMIN)
    if not qs.exists():
        return UserFactory()
    return random.choice(list(qs))


class JobCategoryFactory(DjangoModelFactory):
    class Meta:
        model = JobCategory
        django_get_or_create = ("name",)

    name = Iterator([c["name"] for c in categories])
    icon = Iterator([c["icon"] for c in categories])
    description = Iterator([c["description"] for c in categories])
    color = Iterator([c["color"] for c in categories])
    is_active = Faker("boolean", chance_of_getting_true=95)


class JobFactory(DjangoModelFactory):
    class Meta:
        model = Job
        exclude = ("seed_entry",)

    seed_entry = LazyFunction(lambda: random.choice(JOBS))

    title = LazyAttribute(lambda o: o.seed_entry["title"])
    description = LazyAttribute(lambda o: o.seed_entry["description"])

    thumbnail = factory.django.ImageField(color="gray")

    posted_by = LazyFunction(_random_poster_user)

    # A job posted by an organization account should belong to that
    # organization; individual/freelance posters have none.
    organization = LazyAttribute(
        lambda o: OrganizationProfile.objects.filter(user=o.posted_by).first()
    )

    category = LazyAttribute(lambda o: _get_category(o.seed_entry["category"]))

    location = SubFactory(LocationFactory)

    job_type = Faker("random_element", elements=Job.JobType.values)
    work_mode = Faker("random_element", elements=Job.WorkMode.values)
    status = LazyFunction(
        lambda: random.choices(
            [
                Job.JobStatus.OPEN,
                Job.JobStatus.CLOSED,
                Job.JobStatus.DRAFT,
                Job.JobStatus.PAUSED,
            ],
            weights=[90, 5, 2, 3],
            k=1,
        )[0]
    )
    experience_level = Faker(
        "random_element", elements=Job.ExperienceLevel.values
    )
    experience_years = LazyAttribute(
        lambda o: random.randint(*_EXPERIENCE_YEARS_RANGE[o.experience_level])
    )
    salary_min = LazyAttribute(
        lambda o: random.randint(*_SALARY_RANGE_NPR[o.experience_level])
    )
    salary_max = LazyAttribute(
        lambda o: o.salary_min + random.randint(5_000, 40_000)
    )
    currency = "NPR"
    contact_email = Faker("email")
    contact_phone = LazyFunction(
        lambda: str(random.randint(9800000000, 9899999999))
    )

    requirements = LazyAttribute(lambda o: o.seed_entry["requirements"])
    benefits = LazyAttribute(lambda o: o.seed_entry["benefits"])
    deadline = Faker("date_between", start_date="+1d", end_date="+90d")

    @post_generation
    def skills_required(self, create, extracted, **kwargs):
        if not create:
            return

        job = next((j for j in JOBS if j["title"] == self.title), None)
        if not job:
            return

        skill_names = job.get("skills", [])
        skill_objs = []
        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip().lower())
            skill_objs.append(skill)

        self.skills_required.set(skill_objs)
