import logging

from asgiref.sync import sync_to_async
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _set_online_sync(user_id) -> None:
    try:
        cache.set(
            f"presence_{user_id}", "online", timeout=86400
        )  # expires in 24h as a fallback
    except Exception as exc:
        logger.error("Failed to set presence for user %s: %s", user_id, exc)


def _set_offline_sync(user_id) -> None:
    try:
        cache.delete(f"presence_{user_id}")
    except Exception as exc:
        logger.error("Failed to delete presence for user %s: %s", user_id, exc)


class PresenceService:
    """
    Manages user online presence using Django's default Redis cache.

    `set_online`/`set_offline` are async (thread-pool wrapped) because they're
    called directly from AppConsumer.connect()/disconnect() — an async
    context. `is_online` stays sync/unwrapped since its only caller,
    UserSerializer.get_online(), runs in a sync DRF request.
    """

    set_online = staticmethod(sync_to_async(_set_online_sync))
    set_offline = staticmethod(sync_to_async(_set_offline_sync))

    @staticmethod
    def is_online(user_id) -> bool:
        """Check if a user is online. Sync — call only from sync contexts."""
        try:
            return cache.get(f"presence_{user_id}") == "online"
        except Exception as exc:
            logger.error("Failed to get presence for user %s: %s", user_id, exc)
            return False
