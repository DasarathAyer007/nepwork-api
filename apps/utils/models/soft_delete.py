from typing import TypeVar

from django.db import models
from django.utils import timezone

T = TypeVar("T", bound=models.Model)


class ActiveManager(models.Manager[T]):
    def get_queryset(self) -> models.QuerySet[T]:
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True)
    all_objects = models.Manager()
    objects = ActiveManager()

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def delete(
        self, using: str | None = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        self.soft_delete()
        return (0, {})

    def hard_delete(
        self, using: str | None = None, keep_parents: bool = False
    ) -> None:
        super().delete(using=using, keep_parents=keep_parents)
