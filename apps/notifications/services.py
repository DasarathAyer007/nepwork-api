import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Centralized notification creation + delivery.

    - The `notify_*` builders and `create_and_push` are SYNC and run inside
      Celery workers (outside any async context) — they create the DB row
      and publish it to the recipient's WebSocket group in one call.
    - The remaining staticmethods are ASYNC (`database_sync_to_async`) and
      are used by the WebSocket consumer/handlers for inbound read/unread
      operations.
    """

    # ------------------------------------------------------------------ #
    #  Sync creation + push  (Celery task entrypoints)                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_and_push(
        *,
        recipient_id,
        sender=None,
        notification_type: str,
        title: str,
        message: str,
        entity_type: str = "",
        entity_id: Any = "",
        data: dict | None = None,
    ) -> Notification:
        notification = Notification.objects.create(
            recipient_id=recipient_id,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else "",
            data=data or {},
        )

        payload = NotificationSerializer(notification).data
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{recipient_id}",
            {"type": "notification_new", "payload": payload},
        )
        return notification

    @staticmethod
    def notify_job_application(application) -> Notification:
        job = application.job
        return NotificationService.create_and_push(
            recipient_id=job.posted_by_id,
            sender=application.applicant,
            notification_type=Notification.NotificationType.JOB_APPLICATION_SUBMITTED,
            title="New job application",
            message=(
                f"{application.applicant.username} applied for your job "
                f'"{job.title}".'
            ),
            entity_type="job_application",
            entity_id=application.id,
            data={"job_id": str(job.id)},
        )

    @staticmethod
    def notify_service_request(service_request) -> Notification:
        service = service_request.service
        return NotificationService.create_and_push(
            recipient_id=service.user_id,
            sender=service_request.user,
            notification_type=Notification.NotificationType.SERVICE_REQUEST_SUBMITTED,
            title="New service request",
            message=(
                f"{service_request.user.username} requested your "
                f'"{service.title}" service.'
            ),
            entity_type="service_request",
            entity_id=service_request.id,
            data={"service_id": str(service.id)},
        )

    @staticmethod
    def notify_job_application_status_changed(application) -> Notification:
        job = application.job
        status_label = application.ApplicationStatus(application.status).label
        return NotificationService.create_and_push(
            recipient_id=application.applicant_id,
            sender=application.reviewed_by,
            notification_type=Notification.NotificationType.JOB_APPLICATION_STATUS_CHANGED,
            title="Application status updated",
            message=(
                f'Your application for "{job.title}" has been '
                f"{status_label.lower()}."
            ),
            entity_type="job_application",
            entity_id=application.id,
            data={"job_id": str(job.id), "status": application.status},
        )

    @staticmethod
    def notify_job_application_offer_decision(application) -> Notification:
        job = application.job
        status_label = application.ApplicationStatus(application.status).label
        return NotificationService.create_and_push(
            recipient_id=job.posted_by_id,
            sender=application.applicant,
            notification_type=Notification.NotificationType.JOB_APPLICATION_OFFER_DECISION,
            title="Offer response received",
            message=(
                f"{application.applicant.username} has {status_label.lower()} "
                f'your offer for "{job.title}".'
            ),
            entity_type="job_application",
            entity_id=application.id,
            data={"job_id": str(job.id), "status": application.status},
        )

    @staticmethod
    def notify_service_request_status_changed(
        service_request, actor_id=None
    ) -> Notification:
        service = service_request.service
        status_label = service_request.ServiceRequestStatus(
            service_request.status
        ).label

        requester = service_request.user
        provider = service.user

        # Notify whichever party did NOT perform the transition — e.g. either
        # side can cancel/complete, so the actor already knows what happened.
        # Defaults to notifying the requester (the historical behavior) when
        # the actor is unknown or is the provider.
        if actor_id is not None and str(actor_id) == str(requester.id):
            recipient, sender = provider, requester
            message = (
                f'The service request for "{service.title}" from '
                f"{requester.username} is now {status_label}."
            )
        else:
            recipient, sender = requester, provider
            message = (
                f'Your service request "{service.title}" is now {status_label}.'
            )

        return NotificationService.create_and_push(
            recipient_id=recipient.id,
            sender=sender,
            notification_type=Notification.NotificationType.SERVICE_REQUEST_STATUS_CHANGED,
            title="Service request updated",
            message=message,
            entity_type="service_request",
            entity_id=service_request.id,
            data={
                "service_id": str(service.id),
                "status": service_request.status,
            },
        )

    # ------------------------------------------------------------------ #
    #  Async read / unread  (used by the WebSocket consumer/handlers)     #
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
