from factory.django import DjangoModelFactory
from factory.faker import Faker

from ..models import Skill


class SkillFactory(DjangoModelFactory):
    class Meta:
        model = Skill
        django_get_or_create = ("name",)

    name = Faker("word")
