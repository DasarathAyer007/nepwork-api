import logging

from django.db import migrations
from django.utils import timezone

logger = logging.getLogger(__name__)


def backfill(apps, schema_editor):
    Chat = apps.get_model("chat", "Chat")
    Message = apps.get_model("chat", "Message")

    for chat in Chat.all_objects.all().prefetch_related("members"):
        member_ids = sorted(str(m.id) for m in chat.members.all())

        if len(member_ids) != 2:
            chat.chat_type = "group"
            chat.direct_pair_key = None
            chat.save(update_fields=["chat_type", "direct_pair_key"])
            continue

        chat.chat_type = "direct"
        pair_key = ":".join(member_ids)

        existing = Chat.all_objects.filter(direct_pair_key=pair_key).first()
        if existing is None:
            chat.direct_pair_key = pair_key
            chat.save(update_fields=["chat_type", "direct_pair_key"])
            continue

        if existing.id == chat.id:
            continue

        # Duplicate direct chat for the same pair (pre-existing race). Keep
        # the older chat, move this one's messages onto it, and soft-delete
        # this chat rather than hard-deleting — leaves a manual-review trail.
        older, newer = (
            (existing, chat)
            if existing.created_at <= chat.created_at
            else (chat, existing)
        )

        logger.warning(
            "Merging duplicate direct chat %s into %s (pair_key=%s)",
            newer.id,
            older.id,
            pair_key,
        )
        Message.all_objects.filter(chat_id=newer.id).update(chat_id=older.id)
        older.direct_pair_key = pair_key
        older.chat_type = "direct"
        older.save(update_fields=["chat_type", "direct_pair_key"])

        # Soft-delete the duplicate via the model's own deleted_at field
        # (SoftDeleteModel) rather than hard-deleting — leaves a trail.
        newer.deleted_at = timezone.now()
        newer.direct_pair_key = None
        newer.save(update_fields=["deleted_at", "direct_pair_key"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0002_chat_type_and_direct_pair_key"),
    ]

    operations = [
        migrations.RunPython(backfill, noop_reverse),
    ]
