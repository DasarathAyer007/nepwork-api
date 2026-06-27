from django.db import models

from apps.utils.models import SoftDeleteModel, TimeStampedModel

from .user import User


class Permission(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)

    code = models.CharField(max_length=100, unique=True)

    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class UserPermission(TimeStampedModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="custom_permissions"
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="custom_permissions",
    )
    permission_given_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="permissions_given",
    )

    def __str__(self) -> str:
        return f"{self.user.username} - {self.permission.name}"
