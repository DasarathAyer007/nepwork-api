from uuid import uuid7

from django.db import models

from apps.jobs.models.jobs import Job
from apps.utils.models import SoftDeleteModel, TimeStampedModel


class JobSaved(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="saved_jobs"
    )
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="saved_by"
    )

    class Meta:
        unique_together = ("user", "job")

    def __str__(self):
        return f"{self.user} saved {self.job}"
