import random

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
from apps.users.models.user import User
from apps.users.tests.factories import UserFactory
from apps.utils.json_loader import load_json

data = load_json("apps/jobs/tests/seed_data.json")
categories = data["categories"]
JOBS = data["jobs"]

# ruff: noqa: S311


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

    seed_entry = LazyFunction(lambda: random.choice(JOBS))

    title = LazyAttribute(lambda o: o.seed_entry["title"])
    description = LazyAttribute(lambda o: o.seed_entry["description"])

    posted_by = LazyFunction(
        lambda: random.choice(list(User.objects.all()))
        if User.objects.exists()
        else UserFactory()
    )

    category = LazyAttribute(
        lambda o: JobCategory.objects.get_or_create(
            name=o.seed_entry["category"]
        )[0]
    )

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
    experience_years = Faker("random_int", min=0, max=10)
    salary_min = Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    salary_max = Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    currency = "NPR"
    contact_email = Faker("email")
    contact_phone = LazyFunction(
        lambda: str(random.randint(9800000000, 9899999999))
    )

    requirements = LazyAttribute(lambda o: o.seed_entry["requirements"])
    benefits = LazyAttribute(lambda o: o.seed_entry["benefits"])
    deadline = Faker("date_between", start_date="+1d", end_date="+90d")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Pop seed_entry before creation so it doesn't go to the DB, but keep it for post_generation
        seed_entry = kwargs.pop("seed_entry", None)
        instance = super()._create(model_class, *args, **kwargs)
        instance._seed_entry = seed_entry  # store temporarily on the instance
        return instance

    @post_generation
    def skills_required(self, create, extracted, **kwargs):
        if not create:
            return
        seed_entry = getattr(self, "_seed_entry", None)
        if not seed_entry:
            print("DEBUG: No seed_entry, skipping")
            return
        skill_names = seed_entry.get("skills", [])
        skill_objs = []
        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip().lower())
            skill_objs.append(skill)

        self.skills_required.set(skill_objs)
