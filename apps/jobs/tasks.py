import logging

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_application_status_email(
    self, application_id, status_label: str, message: str
):
    from apps.jobs.models import JobApplication
    from apps.utils.emails.email_service import EmailService

    try:
        application = JobApplication.objects.select_related(
            "job", "applicant"
        ).get(id=application_id)
    except ObjectDoesNotExist:
        logger.warning(
            "send_application_status_email: application %s not found",
            application_id,
        )
        return

    applicant = application.applicant
    if not applicant.email:
        return

    try:
        EmailService.send_application_status_email(
            applicant=applicant,
            job_title=application.job.title,
            status_label=status_label,
            message=message,
        )
    except Exception as exc:
        logger.exception(
            "send_application_status_email failed for application %s",
            application_id,
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_applicant_decision_email(
    self, application_id, decision_label: str, message: str
):
    from apps.jobs.models import JobApplication
    from apps.utils.emails.email_service import EmailService

    try:
        application = JobApplication.objects.select_related(
            "job__posted_by", "applicant"
        ).get(id=application_id)
    except ObjectDoesNotExist:
        logger.warning(
            "send_applicant_decision_email: application %s not found",
            application_id,
        )
        return

    employer = application.job.posted_by
    if not employer.email:
        return

    try:
        EmailService.send_applicant_decision_email(
            employer=employer,
            applicant_name=application.applicant.full_name
            or application.applicant.username,
            job_title=application.job.title,
            decision_label=decision_label,
            message=message,
        )
    except Exception as exc:
        logger.exception(
            "send_applicant_decision_email failed for application %s",
            application_id,
        )
        raise self.retry(exc=exc)
