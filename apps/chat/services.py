import logging
from typing import Any

from channels.db import database_sync_to_async

from .models import Chat, Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)


class ChatService:
    """
    All ORM operations for Chat and Message live here.
    Every method is wrapped in database_sync_to_async so handlers can
    await them directly without blocking the event loop.
    """

    # ------------------------------------------------------------------ #
    #  Membership                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    @database_sync_to_async
    def is_member(user, chat_id) -> bool:
        return Chat.objects.filter(id=chat_id, members=user).exists()

    @staticmethod
    @database_sync_to_async
    def get_member_ids(chat_id) -> list[int]:
        return list(
            Chat.objects.filter(id=chat_id).values_list(
                "members__id", flat=True
            )
        )

    @staticmethod
    @database_sync_to_async
    def get_user_chat_ids(user) -> list:
        """Return all chat UUIDs the user belongs to (used on connect)."""
        return list(user.chats.values_list("id", flat=True))

    # ------------------------------------------------------------------ #
    #  Messages                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    @database_sync_to_async
    def create_message(sender, chat_id, content: str) -> dict[str, Any]:
        message = Message.objects.create(
            chat_id=chat_id,
            sender=sender,
            content=content,
        )
        # Serialize inside the sync context while we still have DB access
        return MessageSerializer(message).data

    @staticmethod
    @database_sync_to_async
    def mark_messages_read(user, chat_id) -> int:
        """Mark all unread messages in a chat as read (excluding user's own)."""
        return (
            Message.objects.filter(
                chat_id=chat_id,
                is_read=False,
            )
            .exclude(sender=user)
            .update(is_read=True)
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
