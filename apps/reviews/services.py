from uuid import UUID

from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.jobs.models import Job
from apps.services.models import Service
from apps.users.models import User

from . import selectors
from .models import Review


class ReviewService:
    @staticmethod
    def _check_not_self_review(reviewer: User, reviewee: User | None) -> None:
        if reviewee is None:
            raise ValidationError(
                "This job or service no longer has an owner to review."
            )
        if reviewer.id == reviewee.id:
            raise ValidationError("You cannot review yourself.")

    @staticmethod
    def _check_not_duplicate_job(reviewer: User, job: Job) -> None:
        if selectors.user_has_reviewed_job(reviewer.id, job.id):
            raise ValidationError("You have already reviewed this job.")

    @staticmethod
    def _check_not_duplicate_service(reviewer: User, service: Service) -> None:
        if selectors.user_has_reviewed_service(reviewer.id, service.id):
            raise ValidationError("You have already reviewed this service.")

    @staticmethod
    def _check_job_review_eligibility(reviewer: User, job: Job) -> None:
        """
        Placeholder for job review eligibility rules.

        Intended final behaviour (per NepWork business rules):
            reviewer must have a JobApplication on this job whose status
            reflects a completed hire (e.g. an "offered"/hired
            application on a job that has since been marked completed).

        Not implemented yet because JobApplication does not currently
        expose a terminal "completed" status distinct from OFFERED /
        REJECTED / WITHDRAWN, and Job does not track a per-application
        completion event. Wire this up once those statuses/fields exist:

            has_valid_application = JobApplication.objects.filter(
                job=job,
                applicant=reviewer,
                status=JobApplication.ApplicationStatus.OFFERED,  # or COMPLETED
            ).exists()
            if not has_valid_application:
                raise PermissionDenied(
                    "You are not eligible to review this job."
                )
        """
        return

    @staticmethod
    def _check_service_review_eligibility(
        reviewer: User, service: Service
    ) -> None:
        """
        Placeholder for service review eligibility rules.

        Intended final behaviour: reviewer must have a ServiceRequest on
        this service with status COMPLETED.

            from apps.services.models import ServiceRequest
            is_eligible = ServiceRequest.objects.filter(
                service=service,
                user=reviewer,
                status=ServiceRequest.ServiceRequestStatus.COMPLETED,
            ).exists()
            if not is_eligible:
                raise PermissionDenied(
                    "You are not eligible to review this service."
                )
        """
        return

    @staticmethod
    def create_job_review(
        *, reviewer: User, job_id: UUID | str, rating: int, comment: str = ""
    ) -> Review:
        job = Job.objects.filter(pk=job_id).first()
        if job is None:
            raise NotFound("The requested job does not exist.")

        reviewee = job.posted_by

        ReviewService._check_not_self_review(reviewer, reviewee)
        ReviewService._check_job_review_eligibility(reviewer, job)
        ReviewService._check_not_duplicate_job(reviewer, job)

        review = Review(
            reviewer=reviewer,
            reviewee=reviewee,
            job=job,
            service=None,
            rating=rating,
            comment=comment,
        )
        review.full_clean()
        review.save()
        return review

    @staticmethod
    def create_service_review(
        *,
        reviewer: User,
        service_id: UUID | str,
        rating: int,
        comment: str = "",
    ) -> Review:
        service = Service.objects.filter(pk=service_id).first()
        if service is None:
            raise NotFound("The requested service does not exist.")

        reviewee = service.user

        ReviewService._check_not_self_review(reviewer, reviewee)
        ReviewService._check_service_review_eligibility(reviewer, service)
        ReviewService._check_not_duplicate_service(reviewer, service)

        review = Review(
            reviewer=reviewer,
            reviewee=reviewee,
            job=None,
            service=service,
            rating=rating,
            comment=comment,
        )
        review.full_clean()
        review.save()
        return review

    @staticmethod
    def update_review(*, review: Review, user: User, **fields) -> Review:
        if review.reviewer_id != user.id:
            raise PermissionDenied("You can only edit your own review.")

        allowed = {"rating", "comment"}
        for key, value in fields.items():
            if key not in allowed:
                continue
            setattr(review, key, value)

        review.full_clean()
        review.save(
            update_fields=[k for k in fields if k in allowed] + ["updated_at"]
        )
        return review

    @staticmethod
    def delete_review(*, review: Review, user: User) -> None:
        is_owner = review.reviewer_id == user.id
        is_staff = user.is_superuser or getattr(user, "is_staff", False)
        if not (is_owner or is_staff):
            raise PermissionDenied(
                "You do not have permission to delete this review."
            )

        review.delete()
