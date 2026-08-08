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

from apps.jobs.models import Job, JobCategory
from apps.locations.tests.factories import LocationFactory
from apps.skill.models import Skill
from apps.users.models import OrganizationProfile, User
from apps.users.tests.factories import UserFactory
from apps.utils.json_loader import load_json
from apps.utils.tests.thumbnail_generator import generate_job_thumbnail

data = load_json("apps/jobs/tests/seed_data.json")
CATEGORIES = data["categories"]
JOBS = data["jobs"]

# ruff: noqa: S311

# Repo layout: <repo_root>/nepwork-api/apps/jobs/tests/factories.py
JOB_ICONS_DIR = Path(__file__).resolve().parent / "seed_image" / "job_category"


def _load_icon_bytes(icon_name: str) -> bytes:
    icon_path = JOB_ICONS_DIR / f"{icon_name}.svg"
    if not icon_path.exists():
        icon_path = JOB_ICONS_DIR / "default.svg"
    return icon_path.read_bytes()


_category_cache: dict[str, JobCategory] = {}


_EXPERIENCE_YEARS_RANGE = {
    Job.ExperienceLevel.ENTRY: (0, 2),
    Job.ExperienceLevel.MID: (2, 5),
    Job.ExperienceLevel.SENIOR: (5, 10),
    Job.ExperienceLevel.LEAD: (8, 15),
}

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
    """Pick a random non-admin user to post the job, favoring organization
    accounts (jobs are mostly posted by companies), falling back to
    creating one so standalone `JobFactory()` calls still work without a
    prior user-seeding step."""
    qs = User.objects.exclude(account_type=User.AccountType.ADMIN)
    if not qs.exists():
        return UserFactory()

    organizations = list(qs.filter(account_type=User.AccountType.ORGANIZATION))
    others = list(qs.exclude(account_type=User.AccountType.ORGANIZATION))

    if organizations and others:
        pool = random.choices([organizations, others], weights=[90, 10], k=1)[0]
    else:
        pool = organizations or others

    return random.choice(pool)


class JobCategoryFactory(DjangoModelFactory):
    class Meta:
        model = JobCategory
        django_get_or_create = ("name",)
        exclude = ("icon_name",)

    name = Iterator([c["name"] for c in CATEGORIES])
    description = Iterator([c["description"] for c in CATEGORIES])
    color = Iterator([c["color"] for c in CATEGORIES])
    is_active = Faker("boolean", chance_of_getting_true=95)

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


class JobFactory(DjangoModelFactory):
    class Meta:
        model = Job
        exclude = ("seed_entry",)

    seed_entry = Iterator(JOBS)

    title = LazyAttribute(lambda o: o.seed_entry["title"])
    description = LazyAttribute(lambda o: o.seed_entry["description"])

    # thumbnail = factory.django.FileField(
    #     filename=LazyAttribute(lambda o: f"{slugify(o.title)}.jpg"),
    #     data=LazyAttribute(
    #         lambda o: generate_job_thumbnail(
    #             title=o.title,
    #             category_name=o.category.name,
    #             skills=o.seed_entry.get("skills", []),
    #             color=o.category.color,
    #         )
    #     ),
    # )

    posted_by = LazyFunction(_random_poster_user)

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

        job = cast(Job, self)

        title = job.title
        category = job.category

        job_data = next(
            (item for item in JOBS if item["title"] == title),
            None,
        )

        if not job_data:
            return

        skill_names = job_data.get("skills", [])

        skill_objs = []

        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip().lower())
            skill_objs.append(skill)

        job.skills_required.set(skill_objs)

        thumbnail = generate_job_thumbnail(
            title=title,
            category_name=category.name,
            skills=skill_names[:4],
            color=category.color,
        )

        job.thumbnail.save(
            f"{slugify(title)}.jpg",
            ContentFile(thumbnail),
            save=True,
        )
