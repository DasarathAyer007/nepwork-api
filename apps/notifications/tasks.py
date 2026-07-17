import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from .services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def notify_job_application(self, application_id):
    from apps.jobs.models import JobApplication

    try:
        application = JobApplication.objects.select_related(
            "job", "job__posted_by", "applicant"
        ).get(id=application_id)
    except ObjectDoesNotExist:
        logger.warning(
            "notify_job_application: application %s not found", application_id
        )
        return

    try:
        NotificationService.notify_job_application(application)
    except Exception as exc:
        logger.exception(
            "notify_job_application failed for application %s", application_id
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def notify_service_request(self, request_id):
    from apps.services.models import ServiceRequest

    try:
        service_request = ServiceRequest.objects.select_related(
            "service", "service__user", "user"
        ).get(id=request_id)
    except ObjectDoesNotExist:
        logger.warning(
            "notify_service_request: request %s not found", request_id
        )
        return

    try:
        NotificationService.notify_service_request(service_request)
    except Exception as exc:
        logger.exception(
            "notify_service_request failed for request %s", request_id
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def notify_job_application_status_changed(self, application_id):
    from apps.jobs.models import JobApplication

    try:
        application = JobApplication.objects.select_related(
            "job", "applicant", "reviewed_by"
        ).get(id=application_id)
    except ObjectDoesNotExist:
        logger.warning(
            "notify_job_application_status_changed: application %s not found",
            application_id,
        )
        return

    try:
        NotificationService.notify_job_application_status_changed(application)
    except Exception as exc:
        logger.exception(
            "notify_job_application_status_changed failed for application %s",
            application_id,
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def notify_service_request_status_changed(self, request_id):
    from apps.services.models import ServiceRequest

    try:
        service_request = ServiceRequest.objects.select_related(
            "service", "service__user", "user"
        ).get(id=request_id)
    except ObjectDoesNotExist:
        logger.warning(
            "notify_service_request_status_changed: request %s not found",
            request_id,
        )
        return

    try:
        NotificationService.notify_service_request_status_changed(
            service_request
        )
    except Exception as exc:
        logger.exception(
            "notify_service_request_status_changed failed for request %s",
            request_id,
        )
        raise self.retry(exc=exc)
