# jobs/query_service_applications.py
from django.db import transaction
from django.db.models import Count, Q
from jsonschema import ValidationError
from rest_framework.exceptions import PermissionDenied

from apps.notifications.tasks import (
    notify_job_application_offer_decision,
    notify_job_application_status_changed,
)

from ..models import JobApplication
from ..selectors.application import get_applications_base
from .application_notifications import (
    notify_applicant_decision,
    notify_application_status_change,
)


class JobApplicationQueryService:
    def __init__(self, user, params: dict | None = None):
        self.user = user
        self.params = params or {}

    def _apply_filters_internal(self, qs, skip_status=False):
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
        if not skip_status and (status := self.params.get("status")):
            qs = qs.filter(status=status)
        if search := self.params.get("search"):
            qs = qs.filter(
                Q(job__title__icontains=search)
                | Q(applicant__full_name__icontains=search)
                | Q(applicant__username__icontains=search)
            )
        if salary_min := self.params.get("expected_salary_min"):
            qs = qs.filter(expected_salary__gte=salary_min)
        if salary_max := self.params.get("expected_salary_max"):
            qs = qs.filter(expected_salary__lte=salary_max)
        if exp_min := self.params.get("years_of_experience_min"):
            qs = qs.filter(years_of_experience__gte=exp_min)
        if exp_max := self.params.get("years_of_experience_max"):
            qs = qs.filter(years_of_experience__lte=exp_max)
        return qs

    def apply_filters(self, qs):
        qs = self._apply_filters_internal(qs)
        ordering = self.params.get("ordering", "-created_at")
        if ordering in ["created_at", "-created_at", "status", "-status"]:
            qs = qs.order_by(ordering)
        return qs

    def status_counts(self) -> dict:
        if not self.user.is_authenticated:
            return {}
        qs = get_applications_base(user=self.user)
        qs = self._apply_filters_internal(qs, skip_status=True)
        counts = {
            status: 0 for status, _ in JobApplication.ApplicationStatus.choices
        }
        for row in qs.values("status").annotate(count=Count("id")):
            counts[row["status"]] = row["count"]
        counts["total"] = sum(counts.values())
        return counts


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
        JobApplication.ApplicationStatus.ACCEPTED,
        JobApplication.ApplicationStatus.DECLINED,
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

        application_id = str(application.id)
        transaction.on_commit(
            lambda: notify_job_application_status_changed.delay(application_id)
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
    def accept_offer(
        cls,
        application,
        user,
        message: str = "",
        send_message: bool = True,
        send_email: bool = True,
    ):
        cls._authorize_applicant(application, user)
        cls._validate_offer_response(application)
        application.status = JobApplication.ApplicationStatus.ACCEPTED
        application.save(update_fields=["status", "updated_at"])
        cls._notify_employer_of_decision(
            application, user, "Accepted", message, send_message, send_email
        )
        return application

    @classmethod
    def decline_offer(
        cls,
        application,
        user,
        message: str = "",
        send_message: bool = True,
        send_email: bool = True,
    ):
        cls._authorize_applicant(application, user)
        cls._validate_offer_response(application)
        application.status = JobApplication.ApplicationStatus.DECLINED
        application.save(update_fields=["status", "updated_at"])
        cls._notify_employer_of_decision(
            application, user, "Declined", message, send_message, send_email
        )
        return application

    @classmethod
    def _notify_employer_of_decision(
        cls,
        application,
        applicant,
        decision_label,
        message,
        send_message,
        send_email,
    ):
        message = (message or "").strip()
        if message:
            notify_applicant_decision(
                application,
                applicant=applicant,
                decision_label=decision_label,
                message=message,
                send_message=send_message,
                send_email=send_email,
            )
        application_id = str(application.id)
        transaction.on_commit(
            lambda: notify_job_application_offer_decision.delay(application_id)
        )

    @classmethod
    def _authorize_employer(cls, application, user):
        if user.account_type != "admin" and user != application.job.posted_by:
            raise PermissionDenied(
                "Only the job owner or an admin can update this application's status."
            )

    @classmethod
    def _authorize_applicant(cls, application, user):
        if user != application.applicant:
            raise PermissionDenied(
                "Only the applicant can perform this action on this application."
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
        if application.status != JobApplication.ApplicationStatus.APPLIED:
            raise ValidationError(
                "An application can only be withdrawn while it is still Applied."
            )

    @classmethod
    def _validate_offer_response(cls, application):
        if application.status != JobApplication.ApplicationStatus.OFFERED:
            raise ValidationError(
                "You can only accept or decline an application that has been offered."
            )
