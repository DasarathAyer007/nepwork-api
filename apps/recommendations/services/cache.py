import json
from typing import cast

from django.conf import settings
from redis import Redis

DEFAULT_TTL_SECONDS = getattr(
    settings, "RECOMMENDATION_CACHE_TTL", 60 * 60
)  # 1 hour

_redis_client = None


def get_redis_client():
    """
    Lazily instantiate a single Redis connection reused across the process.
    Uses a DEDICATED redis_url/db, kept separate from the Celery broker DB
    so a spike in recommendation writes never contends with task queueing.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            getattr(
                settings, "RECOMMENDATION_REDIS_URL", "redis://127.0.0.1:6379/4"
            ),
            decode_responses=True,
        )
    return _redis_client


class RecommendationCache:
    """
    Thin key-value wrapper. Nothing else in the project should build
    recommendation:* keys directly — always go through this class so the
    key format can change in one place later.
    """

    KEY_TEMPLATE = "recommendation:user:{user_id}:{feed_type}"

    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis_client()

    def _key(self, user_id, feed_type):
        return self.KEY_TEMPLATE.format(user_id=user_id, feed_type=feed_type)

    def set(self, user_id, feed_type, items, ttl=DEFAULT_TTL_SECONDS):
        """
        items: list of {"id": int, "score": float} already sorted desc by score.
        """
        key = self._key(user_id, feed_type)
        self.redis.set(key, json.dumps(items), ex=ttl)

    def get(self, user_id, feed_type):
        key = self._key(user_id, feed_type)
        raw = self.redis.get(key)
        if raw is None:
            return None
        return json.loads(cast(str, raw))

    def delete(self, user_id, feed_type=None):
        if feed_type:
            self.redis.delete(self._key(user_id, feed_type))
        else:
            for ft in ("jobs", "services"):
                self.redis.delete(self._key(user_id, ft))

    def exists(self, user_id, feed_type):
        return self.redis.exists(self._key(user_id, feed_type)) == 1
