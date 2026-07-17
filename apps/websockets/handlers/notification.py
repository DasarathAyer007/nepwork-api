import logging

from apps.notifications.services import NotificationService

from .base import BaseHandler

logger = logging.getLogger(__name__)


class NotificationHandler(BaseHandler):
    """
    Handles all inbound notification-related WebSocket messages.

    Supported msg types:
        notification.read      mark a single notification as read
        notification.read_all  mark all notifications as read
    """

    async def handle(self, data: dict):
        action = data.get("type")
        dispatch = {
            "notification.read": self._handle_read,
            "notification.read_all": self._handle_read_all,
        }
        handler_fn = dispatch.get(action)
        if handler_fn:
            await handler_fn(data)
        else:
            await self.send_error(f"Unknown notification action: {action}")

    # ------------------------------------------------------------------ #
    #  notification.read                                                   #
    # ------------------------------------------------------------------ #

    async def _handle_read(self, data: dict):
        notification_id = data.get("notification_id")

        if not notification_id:
            await self.send_error(
                "notification_id is required", "validation_error"
            )
            return

        success = await NotificationService.mark_as_read(
            user=self.user,
            notification_id=notification_id,
        )

        if not success:
            await self.send_error("Notification not found", "not_found")
            return

        unread_count = await NotificationService.get_unread_count(self.user)

        await self.send_to_user(
            user_id=self.user.id,
            event_type="notification_read_confirmed",
            payload={
                "notification_id": notification_id,
                "unread_count": unread_count,
            },
        )

    # ------------------------------------------------------------------ #
    #  notification.read_all                                               #
    # ------------------------------------------------------------------ #

    async def _handle_read_all(self, data: dict):
        updated_count = await NotificationService.mark_all_as_read(self.user)

        await self.send_to_user(
            user_id=self.user.id,
            event_type="notification_read_all_confirmed",
            payload={
                "marked_read": updated_count,
                "unread_count": 0,
            },
        )
