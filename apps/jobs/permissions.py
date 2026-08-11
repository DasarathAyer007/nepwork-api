from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.permissions import (
    IsOwnerAdminOrReadOnly,
    action_for_method,
    get_effective_permission_codes,
    get_user,
)


class IsJobOwnerOrAdminReadOnly(IsOwnerAdminOrReadOnly):
    owner_field = "posted_by"
    resource = "jobs"


class IsJobApplicationOwnerOrAdmin(BasePermission):
    """
    Custom permission for JobApplicationViewSet.
    - Admins require jobs.view for safe methods, and jobs.edit for unsafe/mutating methods.
    - Non-admins can view/withdraw their own applications, or view/change_status of applications to their own jobs.
    """

    def has_permission(self, request, view):
        user = get_user(request)
        if not user or not user.is_authenticated:
            return False

        if user.account_type == "admin":
            if user.is_superuser:
                return True
            action = action_for_method(request.method)
            # Custom status change action is treated as edit
            if view.action in ("change_status", "withdraw", "accept", "reject"):
                action = "edit"
            code = f"jobs.{action}"
            return code in get_effective_permission_codes(user)

        return True

    def has_object_permission(self, request, view, obj):
        user = get_user(request)
        if not user:
            return False

        if user.account_type == "admin":
            return True

        # Non-admins:
        # Check if they are the applicant
        if obj.applicant == user and (
            request.method in SAFE_METHODS
            or view.action in ("withdraw", "accept", "reject")
        ):
            return True

        # Check if they are the employer (job poster)
        return bool(
            obj.job.posted_by == user
            and (
                request.method in SAFE_METHODS or view.action == "change_status"
            )
        )
