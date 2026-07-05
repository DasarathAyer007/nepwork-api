# jobs/query_service_applications.py
from django.db.models import Q
from jsonschema import ValidationError
from rest_framework.exceptions import PermissionDenied

from ..models import JobApplication


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
        if job_id := self.params.get("job_id"):
            qs = qs.filter(job_id=job_id)
        if status := self.params.get("status"):
            qs = qs.filter(status=status)
        ordering = self.params.get("ordering", "-created_at")
        if ordering in ["created_at", "-created_at", "status", "-status"]:
            qs = qs.order_by(ordering)
        return qs


class ApplicationTransitionService:
    VALID_TRANSITIONS = {
        JobApplication.ApplicationStatus.APPLIED: [
            JobApplication.ApplicationStatus.SHORTLISTED,
            JobApplication.ApplicationStatus.REJECTED,
            JobApplication.ApplicationStatus.WITHDRAWN,
        ],
        JobApplication.ApplicationStatus.SHORTLISTED: [
            JobApplication.ApplicationStatus.UNDER_REVIEW,
            JobApplication.ApplicationStatus.REJECTED,
        ],
        JobApplication.ApplicationStatus.UNDER_REVIEW: [
            JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED,
            JobApplication.ApplicationStatus.REJECTED,
        ],
        JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED: [
            JobApplication.ApplicationStatus.INTERVIEWED,
            JobApplication.ApplicationStatus.REJECTED,
        ],
        JobApplication.ApplicationStatus.INTERVIEWED: [
            JobApplication.ApplicationStatus.OFFERED,
            JobApplication.ApplicationStatus.REJECTED,
        ],
        JobApplication.ApplicationStatus.OFFERED: [
            JobApplication.ApplicationStatus.WITHDRAWN,
            # Accept is implicit? Could be a separate status or just stay OFFERED
        ],
    }

    @classmethod
    def transition(cls, application, new_status, user):
        cls._authorize(application, new_status, user)
        cls._validate(application, new_status)
        application.status = new_status
        application.save(update_fields=["status"])
        return application

    @classmethod
    def _authorize(cls, application, new_status, user):
        # Job owner can move to SHORTLISTED, UNDER_REVIEW, INTERVIEW_SCHEDULED, OFFERED, REJECTED
        # Applicant can only WITHDRAW
        allowed = False
        if user == application.job.posted_by:
            allowed = new_status in (
                JobApplication.ApplicationStatus.SHORTLISTED,
                JobApplication.ApplicationStatus.UNDER_REVIEW,
                JobApplication.ApplicationStatus.INTERVIEW_SCHEDULED,
                JobApplication.ApplicationStatus.OFFERED,
                JobApplication.ApplicationStatus.REJECTED,
            )
        elif user == application.applicant:
            allowed = new_status == JobApplication.ApplicationStatus.WITHDRAWN
        if not allowed:
            raise PermissionDenied("Not allowed to perform this status change.")

    @classmethod
    def _validate(cls, application, new_status):
        allowed_next = cls.VALID_TRANSITIONS.get(application.status, [])
        if new_status not in allowed_next:
            raise ValidationError(
                f"Invalid transition from {application.status} to {new_status}."
            )
