import random

from factory.declarations import Iterator, LazyFunction, SubFactory
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
    description = Faker("sentence", nb_words=10)
    is_active = Faker("boolean", chance_of_getting_true=95)


class JobFactory(DjangoModelFactory):
    class Meta:
        model = Job

    title = LazyFunction(lambda: random.choice(JOBS)["title"])

    description = Faker("paragraph", nb_sentences=5)

    posted_by = LazyFunction(
        lambda: (
            random.choice(list(User.objects.all()))
            if User.objects.exists()
            else UserFactory()
        )
    )

    category = LazyFunction(
        lambda: (
            random.choice(list(JobCategory.objects.all()))
            if JobCategory.objects.exists()
            else None
        )
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
        "random_element",
        elements=Job.ExperienceLevel.values,
    )
    experience_years = Faker("random_int", min=0, max=10)
    salary_min = Faker(
        "pydecimal",
        left_digits=4,
        right_digits=2,
        positive=True,
    )
    salary_max = Faker(
        "pydecimal",
        left_digits=4,
        right_digits=2,
        positive=True,
    )
    currency = "NPR"
    contact_email = Faker("email")
    contact_phone = LazyFunction(
        lambda: str(random.randint(9800000000, 9899999999))
    )
    requirements = LazyFunction(
        lambda: random.sample(
            [
                "Bachelor's degree",
                "2+ years experience",
                "Strong communication skills",
                "Problem-solving ability",
                "Team collaboration",
                "Portfolio required",
            ],
            k=3,
        )
    )
    benefits = LazyFunction(
        lambda: random.sample(
            [
                "Health insurance",
                "Remote work",
                "Paid leave",
                "Training budget",
                "Flexible hours",
                "Transport allowance",
            ],
            k=3,
        )
    )
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
