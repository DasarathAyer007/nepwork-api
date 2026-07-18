import logging
from typing import Any

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Case, F, IntegerField, Sum, When

from .models import Chat, Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatService:
    """
    All ORM operations for Chat and Message live here — the single
    definition each is used by both the async WebSocket path (via the
    `database_sync_to_async`-wrapped methods) and the sync HTTP path (via
    the `*_sync` counterparts), so there is exactly one implementation of
    each query, not one per call site.
    """

    # ------------------------------------------------------------------ #
    #  Membership                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_member_sync(user, chat_id) -> bool:
        return Chat.objects.filter(id=chat_id, members=user).exists()

    @staticmethod
    def get_member_ids_sync(chat_id) -> list:
        return list(
            Chat.objects.filter(id=chat_id).values_list(
                "members__id", flat=True
            )
        )

    # database_sync_to_async defaults to thread_sensitive=True, which
    # routes EVERY sync-DB call in the whole process — every chat send,
    # every sync HTTP view under ASGI, everything — onto a single shared
    # worker thread. One slow caller anywhere blocks all chat traffic
    # behind it. Message delivery has no reason to share that thread with
    # unrelated request handling, so the hot chat path runs
    # thread_sensitive=False: real thread-pool concurrency instead of a
    # single-file queue.
    is_member = staticmethod(
        database_sync_to_async(is_member_sync.__func__, thread_sensitive=False)
    )
    get_member_ids = staticmethod(
        database_sync_to_async(
            get_member_ids_sync.__func__, thread_sensitive=False
        )
    )

    @staticmethod
    @database_sync_to_async
    def get_user_chat_ids(user) -> list:
        """Return all chat UUIDs the user belongs to (used on connect)."""
        return list(user.chats.values_list("id", flat=True))

    # ------------------------------------------------------------------ #
    #  Unread counts — single definition, shared by every call site        #
    #  (WS handlers, HTTP views, ChatSerializer)                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _unread_count_queryset(user):
        return Message.objects.filter(
            chat__members=user, is_read=False
        ).exclude(sender=user)

    @staticmethod
    def get_unread_count_sync(user) -> int:
        return ChatService._unread_count_queryset(user).count()

    get_unread_count = staticmethod(
        database_sync_to_async(
            get_unread_count_sync.__func__, thread_sensitive=False
        )
    )

    @staticmethod
    def get_chat_unread_count_sync(chat_id, user) -> int:
        """Per-chat unread count (sidebar badge), distinct from the global
        count above (header badge) — same exclude-own-messages shape, scoped
        to one chat instead of all of the user's chats."""
        return (
            Message.objects.filter(chat_id=chat_id, is_read=False)
            .exclude(sender=user)
            .count()
        )

    # ------------------------------------------------------------------ #
    #  Messages                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_message_sync(sender, chat_id, content: str) -> dict[str, Any]:
        message = Message.objects.create(
            chat_id=chat_id,
            sender=sender,
            content=content,
        )
        return MessageSerializer(message).data

    create_message = staticmethod(
        database_sync_to_async(
            create_message_sync.__func__, thread_sensitive=False
        )
    )

    @staticmethod
    def mark_chat_read_and_get_unread_counts_sync(
        user, chat_id
    ) -> tuple[int, list[dict]]:
        """
        Marks chat messages read for the user, and returns each member's
        updated GLOBAL unread count (across all their chats — matches what
        the header/badge renders).

        Two queries total regardless of member count: the mark-read update,
        then one grouped aggregate computing every member's unread count in
        a single pass (replaces the previous per-member query loop).
        """
        with transaction.atomic():
            updated_count = (
                Message.objects.filter(chat_id=chat_id, is_read=False)
                .exclude(sender=user)
                .update(is_read=True)
            )

            member_ids = ChatService.get_member_ids_sync(chat_id)

            counts_qs = (
                Message.objects.filter(
                    chat__members__id__in=member_ids, is_read=False
                )
                .values("chat__members__id")
                .annotate(
                    unread=Sum(
                        Case(
                            When(sender_id=F("chat__members__id"), then=0),
                            default=1,
                            output_field=IntegerField(),
                        )
                    )
                )
            )
            counts_by_member = {
                row["chat__members__id"]: row["unread"] or 0
                for row in counts_qs
            }

        results = [
            {"member_id": mid, "unread_count": counts_by_member.get(mid, 0)}
            for mid in member_ids
        ]
        return updated_count, results

    mark_chat_read_and_get_unread_counts = staticmethod(
        database_sync_to_async(
            mark_chat_read_and_get_unread_counts_sync.__func__,
            thread_sensitive=False,
        )
    )

    @staticmethod
    @database_sync_to_async
    def get_chat_messages(chat_id, limit: int = 50, offset: int = 0):
        messages = (
            Message.objects.filter(chat_id=chat_id)
            .select_related("sender")
            .order_by("created_at")[offset : offset + limit]
        )
        return MessageSerializer(messages, many=True).data

    # ------------------------------------------------------------------ #
    #  Direct chat get-or-create                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_or_create_direct_chat_sync(users) -> tuple[Chat, bool]:
        """
        The ONLY implementation of "one direct chat per pair" — relies on
        the DB-level unique constraint on `direct_pair_key` (see the Chat
        model) rather than app-level row locking. Two near-simultaneous
        calls for the same pair race on the INSERT; the loser gets an
        IntegrityError and falls back to fetching the winner's row.
        """
        member_ids = {str(u) for u in users}
        if len(member_ids) != 2:
            raise ValueError(
                "Direct chat requires exactly two distinct members"
            )

        pair_key = ":".join(sorted(member_ids))

        try:
            with transaction.atomic():
                chat = Chat.objects.create(
                    chat_type=Chat.ChatType.DIRECT, direct_pair_key=pair_key
                )
                chat.members.add(*member_ids)
            return chat, True
        except IntegrityError:
            return Chat.objects.get(direct_pair_key=pair_key), False

    get_or_create_direct_chat = staticmethod(
        database_sync_to_async(
            get_or_create_direct_chat_sync.__func__, thread_sensitive=False
        )
    )
