from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from ..models import ServiceRequest


class ServiceRequestQueryService:
    ALLOWED_ORDERING = {
        "created_at",
        "-created_at",
        "status",
        "-status",
        "priority",
        "-priority",
        "budget",
        "-budget",
    }
    DEFAULT_ORDERING = "-created_at"

    def __init__(self, user=None, params: dict | None = None):
        self.user = user
        self.params = {} if params is None else params

    def apply_filters(self, qs):
        if self.user and not self.user.is_authenticated:
            return qs.none()

        # If not admin, restrict to owner
        if self.user and self.user.account_type != "admin":
            qs = qs.filter(Q(user=self.user) | Q(service__user=self.user))

        # Filter by perspective: "sent" = requests I made, "received" = requests to my services
        scope = self.params.get("scope")
        if scope == "sent":
            qs = qs.filter(user=self.user)
        elif scope == "received":
            qs = qs.filter(service__user=self.user)

        # Filter by service
        if service_id := self.params.get("service_id"):
            qs = qs.filter(service_id=service_id)

        # Filter by status
        if status_val := self.params.get("status"):
            qs = qs.filter(status=status_val)

        # Filter by priority
        if priority := self.params.get("priority"):
            qs = qs.filter(priority=priority)

        # Ordering
        ordering = self.params.get("ordering", self.DEFAULT_ORDERING)
        if ordering in self.ALLOWED_ORDERING:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by(self.DEFAULT_ORDERING)
        return qs


class ServiceRequestTransitionService:
    """
    Handle state transition rule for a ServiceRequest.
    """

    VALID_TRANSITIONS = {
        ServiceRequest.ServiceRequestStatus.OPEN: [
            ServiceRequest.ServiceRequestStatus.ACCEPTED,
            ServiceRequest.ServiceRequestStatus.REJECTED,
            ServiceRequest.ServiceRequestStatus.CANCELLED,
        ],
        ServiceRequest.ServiceRequestStatus.ACCEPTED: [
            ServiceRequest.ServiceRequestStatus.IN_PROGRESS,
            ServiceRequest.ServiceRequestStatus.CANCELLED,
        ],
        ServiceRequest.ServiceRequestStatus.IN_PROGRESS: [
            # Once work has started, the requester can no longer cancel —
            # only the provider can mark it complete.
            ServiceRequest.ServiceRequestStatus.COMPLETED,
        ],
    }

    @classmethod
    def transition(
        cls, request_instance: ServiceRequest, new_status: str, user
    ) -> ServiceRequest:
        """
        Attempt to transition the given request to `new_status`.
        """
        cls._authorize(request_instance, new_status, user)
        cls._validate_transition(request_instance, new_status)

        request_instance.status = new_status
        if new_status == ServiceRequest.ServiceRequestStatus.COMPLETED:
            request_instance.completed_at = timezone.now()
        request_instance.save(update_fields=["status", "completed_at"])
        return request_instance

    @classmethod
    def _authorize(cls, request_instance, new_status, user):
        """Check whether the user can perform this transition."""
        allowed = False

        # Service owner can accept / reject / complete / start progress
        if new_status in (
            ServiceRequest.ServiceRequestStatus.ACCEPTED,
            ServiceRequest.ServiceRequestStatus.REJECTED,
            ServiceRequest.ServiceRequestStatus.COMPLETED,
            ServiceRequest.ServiceRequestStatus.IN_PROGRESS,
        ):
            allowed = user == request_instance.service.user

        # Both service owner and requester can cancel
        elif new_status == ServiceRequest.ServiceRequestStatus.CANCELLED:
            allowed = (
                user == request_instance.user
                or user == request_instance.service.user
            )

        if not allowed:
            raise PermissionDenied(
                "You do not have permission to perform this action."
            )

    @classmethod
    def _validate_transition(cls, request_instance, new_status):
        """Ensure the status transition is valid."""
        allowed_next = cls.VALID_TRANSITIONS.get(request_instance.status, [])
        if new_status not in allowed_next:
            raise ValidationError(
                f"Cannot change status from '{request_instance.status}' to '{new_status}'."
            )
