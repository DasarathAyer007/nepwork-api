from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.jobs.models import Job, JobApplication
from apps.services.models import Service, ServiceRequest
from apps.users.tests.factories import UserFactory

from .models import Notification
from .services import NotificationService


def _make_job(posted_by):
    return Job.objects.create(
        title="Frontend Developer", description="Build UIs", posted_by=posted_by
    )


def _make_job_application(job, applicant):
    return JobApplication.objects.create(job=job, applicant=applicant)


def _make_service(user):
    return Service.objects.create(title="Logo Design", user=user)


def _make_service_request(service, requester):
    return ServiceRequest.objects.create(service=service, user=requester)


class NotificationServiceTests(APITestCase):
    """
    `create_and_push` and the `notify_*` builders run inside Celery workers
    (sync context) — patch out the channel layer so these stay pure unit
    tests with no dependency on a running Redis/Channels backend.
    """

    def setUp(self):
        self.employer = UserFactory(
            username="employer1", email="employer1@test.local"
        )
        self.applicant = UserFactory(
            username="applicant1", email="applicant1@test.local"
        )
        self.provider = UserFactory(
            username="provider1", email="provider1@test.local"
        )
        self.customer = UserFactory(
            username="customer1", email="customer1@test.local"
        )

    @patch("apps.notifications.services.async_to_sync")
    @patch("apps.notifications.services.get_channel_layer")
    def test_create_and_push_creates_notification_and_pushes(
        self, mock_get_channel_layer, mock_async_to_sync
    ):
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        sender_fn = MagicMock()
        mock_async_to_sync.return_value = sender_fn

        notification = NotificationService.create_and_push(
            recipient_id=self.applicant.id,
            sender=self.employer,
            notification_type=Notification.NotificationType.JOB_APPLICATION_SUBMITTED,
            title="New job application",
            message="Someone applied.",
            entity_type="job_application",
            entity_id="abc-123",
            data={"job_id": "xyz"},
        )

        self.assertTrue(
            Notification.objects.filter(id=notification.id).exists()
        )
        self.assertEqual(notification.recipient_id, self.applicant.id)
        self.assertFalse(notification.is_read)

        mock_async_to_sync.assert_called_once_with(
            mock_channel_layer.group_send
        )
        sender_fn.assert_called_once()
        group_name, event = sender_fn.call_args[0]
        self.assertEqual(group_name, f"user_{self.applicant.id}")
        self.assertEqual(event["type"], "notification_new")
        self.assertEqual(event["payload"]["title"], "New job application")

    @patch("apps.notifications.services.async_to_sync")
    @patch("apps.notifications.services.get_channel_layer")
    def test_notify_job_application(self, mock_get_channel_layer, _mock_a2s):
        job = _make_job(posted_by=self.employer)
        application = _make_job_application(job, self.applicant)

        notification = NotificationService.notify_job_application(application)

        self.assertEqual(notification.recipient_id, self.employer.id)
        self.assertEqual(notification.sender_id, self.applicant.id)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.JOB_APPLICATION_SUBMITTED,
        )
        self.assertEqual(notification.entity_type, "job_application")
        self.assertEqual(notification.entity_id, str(application.id))
        self.assertEqual(notification.data["job_id"], str(job.id))
        self.assertIn(job.title, notification.message)

    @patch("apps.notifications.services.async_to_sync")
    @patch("apps.notifications.services.get_channel_layer")
    def test_notify_service_request(self, mock_get_channel_layer, _mock_a2s):
        service = _make_service(user=self.provider)
        service_request = _make_service_request(service, self.customer)

        notification = NotificationService.notify_service_request(
            service_request
        )

        self.assertEqual(notification.recipient_id, self.provider.id)
        self.assertEqual(notification.sender_id, self.customer.id)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.SERVICE_REQUEST_SUBMITTED,
        )
        self.assertEqual(notification.entity_type, "service_request")
        self.assertEqual(notification.entity_id, str(service_request.id))

    @patch("apps.notifications.services.async_to_sync")
    @patch("apps.notifications.services.get_channel_layer")
    def test_notify_job_application_status_changed(
        self, mock_get_channel_layer, _mock_a2s
    ):
        job = _make_job(posted_by=self.employer)
        application = _make_job_application(job, self.applicant)
        application.status = JobApplication.ApplicationStatus.SHORTLISTED
        application.reviewed_by = self.employer
        application.save(update_fields=["status", "reviewed_by"])

        notification = (
            NotificationService.notify_job_application_status_changed(
                application
            )
        )

        self.assertEqual(notification.recipient_id, self.applicant.id)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.JOB_APPLICATION_STATUS_CHANGED,
        )
        self.assertEqual(notification.data["status"], "shortlisted")

    @patch("apps.notifications.services.async_to_sync")
    @patch("apps.notifications.services.get_channel_layer")
    def test_notify_service_request_status_changed(
        self, mock_get_channel_layer, _mock_a2s
    ):
        service = _make_service(user=self.provider)
        service_request = _make_service_request(service, self.customer)
        service_request.status = ServiceRequest.ServiceRequestStatus.ACCEPTED
        service_request.save(update_fields=["status"])

        notification = (
            NotificationService.notify_service_request_status_changed(
                service_request
            )
        )

        self.assertEqual(notification.recipient_id, self.customer.id)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.SERVICE_REQUEST_STATUS_CHANGED,
        )
        self.assertEqual(notification.data["status"], "accepted")


class NotificationViewsTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(
            username="notifuser", email="notifuser@test.local"
        )
        self.other_user = UserFactory(
            username="otheruser", email="otheruser@test.local"
        )
        self.client.force_authenticate(self.user)

        self.notifications = [
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.JOB_APPLICATION_SUBMITTED,
                title=f"Notification {i}",
                message="msg",
            )
            for i in range(15)
        ]
        # A notification belonging to someone else must never leak through.
        Notification.objects.create(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.JOB_APPLICATION_SUBMITTED,
            title="Not yours",
            message="msg",
        )

    def test_unread_count(self):
        response = self.client.get(reverse("notification-unread-count"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 15)

    def test_latest_returns_at_most_ten_newest_first(self):
        response = self.client.get(reverse("notification-latest"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 10)
        newest_first = [n.id for n in reversed(self.notifications)][:10]
        self.assertEqual([n["id"] for n in response.data], newest_first)

    def test_list_is_paginated_and_scoped_to_recipient(self):
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 15)
        self.assertLessEqual(len(response.data["results"]), 20)

    def test_mark_single_notification_read(self):
        target = self.notifications[0]
        response = self.client.patch(
            reverse("notification-read", args=[target.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        target.refresh_from_db()
        self.assertTrue(target.is_read)

    def test_cannot_mark_another_users_notification_read(self):
        others = Notification.objects.get(recipient=self.other_user)
        response = self.client.patch(
            reverse("notification-read", args=[others.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read(self):
        response = self.client.post(reverse("notification-read-all"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["marked_read"], 15)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user, is_read=False
            ).count(),
            0,
        )

    def test_delete_notification(self):
        target = self.notifications[0]
        response = self.client.delete(
            reverse("notification-delete", args=[target.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Notification.objects.filter(id=target.id).exists())
