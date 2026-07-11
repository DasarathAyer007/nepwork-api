# jobs/query_service_applications.py
from django.db.models import Q
from jsonschema import ValidationError
from rest_framework.exceptions import PermissionDenied

from ..models import JobApplication
from .application_notifications import notify_application_status_change


class JobApplicationQueryService:
    def __init__(self, user, params: dict | None = None):
        self.user = user
        self.params = params or {}

    def apply_filters(self, qs):
        if not self.user.is_authenticated:
            return qs.none()
        # If not admin, restrict to own applications or applications to own jobs
        if self.user.account_type != "admin":
            qs = qs.filter(Q(applicant=self.user) | Q(job__posted_by=self.user))
        scope = self.params.get("scope")
        if scope == "applied":
            qs = qs.filter(applicant=self.user)
        elif scope == "received":
            qs = qs.filter(job__posted_by=self.user)
        if job_id := self.params.get("job_id"):
            qs = qs.filter(job_id=job_id)
        if status := self.params.get("status"):
            qs = qs.filter(status=status)
        ordering = self.params.get("ordering", "-created_at")
        if ordering in ["created_at", "-created_at", "status", "-status"]:
            qs = qs.order_by(ordering)
        return qs


class ApplicationTransitionService:
    """
    Employer-driven status changes are free-form among the non-terminal
    statuses (no fixed sequence) — the employer can jump straight to
    "interviewed" or move a candidate back to "under_review", for example.
    Only REJECTED and WITHDRAWN are terminal; once an application reaches
    one of those, no further status changes are allowed.
    """

    TERMINAL_STATUSES = {
        JobApplication.ApplicationStatus.REJECTED,
        JobApplication.ApplicationStatus.WITHDRAWN,
    }

    # Statuses an employer may move an application into.
    EMPLOYER_STATUSES = [
        JobApplication.ApplicationStatus.SHORTLISTED,
        JobApplication.ApplicationStatus.UNDER_REVIEW,
        JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplication.ApplicationStatus.INTERVIEWED,
        JobApplication.ApplicationStatus.OFFERED,
        JobApplication.ApplicationStatus.REJECTED,
    ]

    # Statuses that offer the employer the option to send the applicant a
    # message (via chat and/or email) — never required, just available.
    MESSAGE_CAPABLE_STATUSES = {
        JobApplication.ApplicationStatus.SHORTLISTED,
        JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplication.ApplicationStatus.OFFERED,
        JobApplication.ApplicationStatus.REJECTED,
    }

    @classmethod
    def change_status(
        cls,
        application,
        new_status,
        user,
        message: str = "",
        send_message: bool = True,
        send_email: bool = True,
    ):
        cls._authorize_employer(application, user)
        cls._validate_employer_transition(application, new_status)

        message = (message or "").strip()

        application.status = new_status
        application.reviewed_by = user
        application.save(update_fields=["status", "reviewed_by", "updated_at"])

        if message:
            notify_application_status_change(
                application,
                employer=user,
                status_label=str(
                    JobApplication.ApplicationStatus(new_status).label
                ),
                message=message,
                send_message=send_message,
                send_email=send_email,
            )

        return application

    @classmethod
    def withdraw(cls, application, user):
        cls._authorize_applicant(application, user)
        cls._validate_withdraw(application)
        application.status = JobApplication.ApplicationStatus.WITHDRAWN
        application.save(update_fields=["status"])
        return application

    @classmethod
    def _authorize_employer(cls, application, user):
        if user != application.job.posted_by:
            raise PermissionDenied(
                "Only the job owner can update this application's status."
            )

    @classmethod
    def _authorize_applicant(cls, application, user):
        if user != application.applicant:
            raise PermissionDenied(
                "Only the applicant can withdraw this application."
            )

    @classmethod
    def _validate_employer_transition(cls, application, new_status):
        if application.status in cls.TERMINAL_STATUSES:
            raise ValidationError(
                f"Cannot change status from {application.status}."
            )
        if new_status not in cls.EMPLOYER_STATUSES:
            raise ValidationError(f"Invalid status: {new_status}.")
        if new_status == application.status:
            raise ValidationError("Application is already in this status.")

    @classmethod
    def _validate_withdraw(cls, application):
        if application.status in cls.TERMINAL_STATUSES:
            raise ValidationError(
                f"Cannot withdraw an application that is already {application.status}."
            )
