import logging
from typing import Any

from channels.db import database_sync_to_async

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationService:
    """
    All ORM operations for Notification live here.
    Also used by ChatHandler to create and push notifications when
    a new message is sent.
    """

    # ------------------------------------------------------------------ #
    #  Creation                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    @database_sync_to_async
    def create_notification(
        recipient_id: int,
        sender,
        title: str,
        message: str,
        action_url: str = "",
    ) -> dict[str, Any]:
        notification = Notification.objects.create(
            recipient_id=recipient_id,
            sender=sender,
            title=title,
            message=message,
            action_url=action_url,
        )
        return NotificationSerializer(notification).data

    # ------------------------------------------------------------------ #
    #  Read / unread                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    @database_sync_to_async
    def mark_as_read(user, notification_id) -> bool:
        updated = Notification.objects.filter(
            id=notification_id,
            recipient=user,
            is_read=False,
        ).update(is_read=True)
        return updated > 0

    @staticmethod
    @database_sync_to_async
    def mark_all_as_read(user) -> int:
        return Notification.objects.filter(
            recipient=user,
            is_read=False,
        ).update(is_read=True)

    @staticmethod
    @database_sync_to_async
    def get_unread_count(user) -> int:
        return Notification.objects.filter(
            recipient=user, is_read=False
        ).count()

    # ------------------------------------------------------------------ #
    #  Listing                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    @database_sync_to_async
    def get_notifications(user, limit: int = 20, offset: int = 0):
        notifications = (
            Notification.objects.filter(recipient=user)
            .select_related("sender")
            .order_by("-created_at")[offset : offset + limit]
        )
        return NotificationSerializer(notifications, many=True).data
