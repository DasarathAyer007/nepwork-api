from uuid import uuid7

from django.db import models

from apps.utils.models.soft_delete import SoftDeleteModel
from apps.utils.models.timestamp import TimeStampedModel


class Chat(TimeStampedModel, SoftDeleteModel):
    class ChatType(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=255, blank=True)
    members = models.ManyToManyField("users.User", related_name="chats")
    chat_type = models.CharField(
        max_length=10, choices=ChatType.choices, default=ChatType.DIRECT
    )
    # "{min_member_id}:{max_member_id}" for direct chats only — a real DB
    # constraint (unique=True) enforcing "one direct chat per pair", instead
    # of relying solely on app-level select_for_update locking. Null for
    # group chats, which have no such uniqueness requirement.
    direct_pair_key = models.CharField(
        max_length=80, null=True, blank=True, unique=True
    )

    def __str__(self):
        return self.name or f"Chat {self.id}"
