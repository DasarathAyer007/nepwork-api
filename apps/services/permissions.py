from rest_framework.permissions import BasePermission

from apps.users.permissions import IsOwnerAdminOrReadOnly, action_for_method
from apps.users.services.permissions import get_effective_permission_codes


class IsServiceOwnerOrAdmin(IsOwnerAdminOrReadOnly):
    owner_field = "user"
    resource = "services"


class IsServiceRequestParticipantOrAdmin(BasePermission):
    """Either side of a ServiceRequest (requester or the service's owner)
    can view and act on it; only the requester may delete it. An admin who
    is neither party may still act if their effective permissions include
    `services.{action}` for this request's method (not a blanket bypass)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        is_requester = obj.user_id == user.id
        is_provider = obj.service.user_id == user.id

        if request.method == "DELETE":
            if is_requester:
                return True
        elif is_requester or is_provider:
            return True

        if user.is_superuser:
            return True

        code = f"services.{action_for_method(request.method)}"
        return code in get_effective_permission_codes(user)
