import logging

from .services import ActivityTracker

logger = logging.getLogger(__name__)

_UNSET = object()


class ActivityTrackingMixin:
    """
    Mixin for DRF ViewSets that need to record user activity. Feature-agnostic:
    it knows nothing about Jobs/Services, it just forwards to ActivityTracker.

        class JobViewSet(ActivityTrackingMixin, ModelViewSet):
            activity_object_type = ObjectType.JOB

            def perform_create(self, serializer):
                serializer.save(...)
                self.track_activity(ActivityType.APPLY, object_id=serializer.instance.job_id)
    """

    activity_object_type = None
    activity_requires_auth = True

    def track_activity(
        self, activity_type, object_type=_UNSET, object_id=None, metadata=None
    ):
        """
        Records a user activity. Never raises — tracking must not break or
        delay the actual API response.

        `object_type` defaults to `self.activity_object_type` when omitted;
        pass `object_type=None` explicitly for activities with no associated
        object (e.g. a SEARCH event that isn't about one specific item).
        """
        request = self.request
        if self.activity_requires_auth and not (
            request.user and request.user.is_authenticated
        ):
            return

        resolved_object_type = (
            self.activity_object_type if object_type is _UNSET else object_type
        )
        try:
            ActivityTracker.track(
                user_id=request.user.id,
                activity_type=activity_type,
                object_type=resolved_object_type,
                object_id=object_id,
                metadata=metadata,
            )
        except Exception:
            logger.exception("Activity tracking failed for %s", request.path)
