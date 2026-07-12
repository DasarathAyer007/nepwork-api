import logging

logger = logging.getLogger(__name__)


class ActivityTracker:
    """
    Entry point every view/serializer/signal in the project should call.
    This is the ONLY public API of this app for writing activity — it never
    touches the database itself, it only dispatches a Celery task, so the
    calling request returns immediately.
    """

    @staticmethod
    def track(
        user_id, activity_type, object_type=None, object_id=None, metadata=None
    ):
        from .tasks import create_user_activity

        create_user_activity.delay(
            user_id=user_id,
            activity_type=activity_type,
            object_type=object_type,
            object_id=str(object_id) if object_id is not None else None,
            metadata=metadata or {},
        )
        logger.info(
            "Dispatched create_user_activity: user_id=%s activity_type=%s object_type=%s object_id=%s",
            user_id,
            activity_type,
            object_type,
            object_id,
        )
