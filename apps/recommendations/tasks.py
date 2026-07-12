import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="recommendations.update_user_recommendations", bind=True, max_retries=3
)
def update_user_recommendations(self, user_id):
    """
    Triggered by user_activity.tasks.create_user_activity after every
    relevant event. Recomputes and overwrites the user's cached
    recommendation feeds in Redis. Never touches Postgres for storage —
    read-only queries against Job/Service only.
    """
    from .services.engine import RecommendationEngine

    try:
        engine = RecommendationEngine()
        result = engine.generate_for_user(user_id)
        logger.info(
            "Recomputed recommendations for user_id=%s (jobs=%d, services=%d)",
            user_id,
            len(result["jobs"]),
            len(result["services"]),
        )
        return result
    except Exception as exc:
        logger.exception(
            "Failed to update recommendations for user_id=%s", user_id
        )
        raise self.retry(exc=exc, countdown=10)


@shared_task(name="recommendations.refresh_all_active_users")
def refresh_all_active_users(days=7):
    """
    Optional Celery Beat job (e.g. hourly) to proactively warm/refresh
    recommendations for recently-active users, so the cache rarely misses
    even after the 30-60min TTL expires between visits.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.user_activity.models import UserActivity

    since = timezone.now() - timedelta(days=days)
    user_ids = (
        UserActivity.objects.filter(created_at__gte=since)
        .values_list("user_id", flat=True)
        .distinct()
    )
    for user_id in user_ids:
        update_user_recommendations.delay(user_id=user_id)

    return len(user_ids) if hasattr(user_ids, "__len__") else "dispatched"
