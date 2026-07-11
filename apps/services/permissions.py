from rest_framework.permissions import BasePermission

from apps.users.permissions import IsOwnerAdminOrReadOnly


class IsServiceOwnerOrAdmin(IsOwnerAdminOrReadOnly):
    owner_field = "user"


class IsServiceRequestParticipantOrAdmin(BasePermission):
    """Either side of a ServiceRequest (requester or the service's owner)
    can view and act on it; only the requester may delete it."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "account_type", None) == "admin":
            return True

        is_requester = obj.user_id == user.id
        is_provider = obj.service.user_id == user.id

        if request.method == "DELETE":
            return is_requester

        return is_requester or is_provider
