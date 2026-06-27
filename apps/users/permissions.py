from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.models import User


class BaseRolePermission(BasePermission):
    """
    Handles role-based access (organization, individual, admin)
    """

    required_role: str | None = None

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = get_user(request)

        if not user or not user.is_authenticated:
            return False

        if user.account_type == "admin":
            return True

        if self.required_role is None:
            return True

        return user.account_type == self.required_role


class IsOrganization(BaseRolePermission):
    required_role = "organization"


class IsIndividual(BaseRolePermission):
    required_role = "individual"


class IsAdmin(BaseRolePermission):
    required_role = "admin"


class IsOwnerAdminOrReadOnly(BasePermission):
    owner_field = "created_by"

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True

        user = get_user(request)

        return bool(user and user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True

        user = get_user(request)

        if user is None or not user.is_authenticated:
            return False

        if user.account_type == "admin":
            return True

        owner_id = getattr(obj, f"{self.owner_field}_id", None)

        return owner_id == user.id


def get_user(request: Request) -> User | None:
    user = request.user

    if not user.is_authenticated:
        return None

    return user
