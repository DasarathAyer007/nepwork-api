from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.permissions import action_for_method
from apps.users.services.permissions import get_effective_permission_codes


class IsReviewOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if obj.reviewer_id == user.id:
            # Owners may PATCH or DELETE their own review.
            return True

        if user.is_superuser:
            return True

        code = f"reviews.{action_for_method(request.method)}"
        return code in get_effective_permission_codes(user)
