from uuid import uuid7

from django.db import models


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
