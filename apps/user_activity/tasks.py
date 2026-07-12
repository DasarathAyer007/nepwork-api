import logging

from celery import shared_task

logger = logging.getLogger(__name__)

RECOMMENDABLE_OBJECT_TYPES = {"JOB", "SERVICE"}


@shared_task(
    name="user_activity.create_user_activity", bind=True, max_retries=3
)
def create_user_activity(
    self,
    user_id,
    activity_type,
    object_type=None,
    object_id=None,
    metadata=None,
):
    """
    Saves a UserActivity row, then fire-and-forgets a recommendation
    recompute for the user. Contains no recommendation logic itself.
    """
    from .models import UserActivity

    try:
        activity = UserActivity.objects.create(
            user_id=user_id,
            activity_type=activity_type,
            object_type=object_type or "",
            object_id=object_id or "",
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.exception("Failed to save UserActivity for user_id=%s", user_id)
        raise self.retry(exc=exc, countdown=5)

    if activity_type == "SEARCH" or object_type in RECOMMENDABLE_OBJECT_TYPES:
        from apps.recommendations.tasks import update_user_recommendations

        update_user_recommendations.delay(user_id=user_id)

    return activity.id
