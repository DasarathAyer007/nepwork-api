import logging

from apps.chat.services import ChatService
from apps.notifications.services import NotificationService

from .base import BaseHandler

logger = logging.getLogger(__name__)


class ChatHandler(BaseHandler):
    """
    Handles all inbound chat-related WebSocket messages.

    Supported msg types:
        chat.send    - user sends a message to a conversation
        chat.typing  - user is typing / stopped typing
        chat.read    - user has read up to a certain message
    """

    async def handle(self, data: dict):
        action = data.get("type")
        dispatch = {
            "chat.send": self._handle_send,
            "chat.typing": self._handle_typing,
            "chat.read": self._handle_read,
        }
        handler_fn = dispatch.get(action)
        if handler_fn:
            await handler_fn(data)
        else:
            await self.send_error(f"Unknown chat action: {action}")

    # ------------------------------------------------------------------ #
    #  chat.send                                                           #
    # ------------------------------------------------------------------ #

    async def _handle_send(self, data: dict):
        chat_id = data.get("chat_id")
        content = data.get("content", "").strip()

        if not chat_id or not content:
            await self.send_error(
                "chat_id and content are required", "validation_error"
            )
            return

        # Verify sender is a member of this chat
        is_member = await ChatService.is_member(self.user, chat_id)
        if not is_member:
            await self.send_error(
                "You are not a member of this chat", "forbidden"
            )
            return

        # Persist the message
        message = await ChatService.create_message(
            sender=self.user,
            chat_id=chat_id,
            content=content,
        )

        # Deliver via each member's PERSONAL group (user_{id}), not a
        # chat-room group. Personal groups are joined once at connect() and
        # never go stale — so this works identically whether the chat is
        # brand new (just created via HTTP, this is its first message) or
        # years old. No group-membership bookkeeping needed anywhere.
        member_ids = await ChatService.get_member_ids(chat_id)
        for member_id in member_ids:
            await self.send_to_user(
                user_id=member_id,
                event_type="chat_message",  # → AppConsumer.chat_message()
                payload=message,
            )

            if member_id == self.user.id:
                continue  # don't notify yourself

            notification = await NotificationService.create_notification(
                recipient_id=member_id,
                sender=self.user,
                title=f"New message from {self.user.username}",
                message=content[:100],
                action_url=f"/chats/{chat_id}/",
            )
            await self.send_to_user(
                user_id=member_id,
                event_type="notification_new",  # → AppConsumer.notification_new()
                payload=notification,
            )

    # ------------------------------------------------------------------ #
    #  chat.typing                                                         #
    # ------------------------------------------------------------------ #

    async def _handle_typing(self, data: dict):
        chat_id = data.get("chat_id")
        is_typing = data.get("is_typing", False)

        if not chat_id:
            await self.send_error("chat_id is required", "validation_error")
            return

        is_member = await ChatService.is_member(self.user, chat_id)
        if not is_member:
            await self.send_error(
                "You are not a member of this chat", "forbidden"
            )
            return

        member_ids = await ChatService.get_member_ids(chat_id)
        for member_id in member_ids:
            if member_id == self.user.id:
                continue  # don't echo typing back to the typer
            await self.send_to_user(
                user_id=member_id,
                event_type="typing_indicator",  # → AppConsumer.typing_indicator()
                payload={
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "is_typing": is_typing,
                    "chat_id": str(chat_id),
                },
            )

    # ------------------------------------------------------------------ #
    #  chat.read                                                           #
    # ------------------------------------------------------------------ #

    async def _handle_read(self, data: dict):
        chat_id = data.get("chat_id")

        if not chat_id:
            await self.send_error("chat_id is required", "validation_error")
            return

        updated_count = await ChatService.mark_messages_read(
            user=self.user,
            chat_id=chat_id,
        )

        # Echo back confirmation to the sender only
        await self.reply(
            "chat.read_confirmed",
            {
                "chat_id": str(chat_id),
                "marked_read": updated_count,
            },
        )
