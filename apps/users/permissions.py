from collections.abc import Sequence

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.models import User
from apps.users.services.permissions import (
    get_effective_permission_codes,
    get_role_rank,
    is_superadmin,
)


def action_for_method(method: str | None) -> str:
    if method in SAFE_METHODS:
        return "view"
    if method == "DELETE":
        return "delete"
    return "edit"


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


class IsSuperAdmin(BasePermission):
    """Passes only for an actual superadmin (Django is_superuser flag OR
    AdminProfile.role.code == 'superadmin'). Used to gate operations that
    must never be delegable via a permission code, e.g. editing a role's
    default permission set."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_superadmin(get_user(request))


class CanManageAdminUser(BasePermission):
    """Object-level check for updating an existing admin account: the
    requester must be strictly senior (lower rank) than the target admin's
    current role, or be a superadmin (who may manage anyone)."""

    def has_object_permission(
        self, request: Request, view: APIView, obj: object
    ) -> bool:
        user = get_user(request)
        if user is None:
            return False

        if is_superadmin(user):
            return True

        target_user = getattr(obj, "user", obj)
        return get_role_rank(user) < get_role_rank(target_user)


class IsAdminOrReadOnly(BasePermission):
    """Safe methods are open to everyone; writes require the requester to
    hold `{resource}.edit`/`{resource}.delete` (superuser bypasses).

    Usage: permission_classes = [IsAdminOrReadOnly("jobs")]
    """

    def __init__(self, resource: str):
        self.resource = resource

    def __call__(self) -> "IsAdminOrReadOnly":
        return self

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True

        user = get_user(request)
        if not user:
            return False

        if user.is_superuser:
            return True

        code = f"{self.resource}.{action_for_method(request.method)}"
        return code in get_effective_permission_codes(user)


class IsOwnerAdminOrReadOnly(BasePermission):
    """Owner of the object may act on it; otherwise an admin may act on it
    ONLY if their effective permissions include `{resource}.{action}` for
    the request method (view/edit/delete) — NOT a blanket admin bypass.
    Subclasses set `owner_field` and `resource`.
    """

    owner_field = "created_by"
    resource: str | None = None

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

        if user is None:
            return False

        owner_id = getattr(obj, f"{self.owner_field}_id", None)
        if owner_id == user.id:
            return True

        if user.is_superuser:
            return True

        if self.resource:
            code = f"{self.resource}.{action_for_method(request.method)}"
            return code in get_effective_permission_codes(user)

        return False


class HasPermission(BasePermission):
    """
    Grants access if the requesting user holds ANY of the given permission
    code(s) (resolved via the centralized get_effective_permission_codes
    service). Superusers always pass.

    Usage:
        permission_classes = [IsAuthenticated, HasPermission("jobs.edit")]
        permission_classes = [IsAuthenticated, HasPermission(["jobs.view", "jobs.edit"])]
    """

    def __init__(self, codes: str | Sequence[str]):
        self.codes = [codes] if isinstance(codes, str) else list(codes)

    def __call__(self) -> "HasPermission":
        # DRF instantiates permission_classes entries with no args; since
        # HasPermission(...) is already an instance, returning self lets it
        # be used directly inside a permission_classes list/tuple.
        return self

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = get_user(request)

        if not user:
            return False

        if user.is_superuser:
            return True

        effective = get_effective_permission_codes(user)

        return any(code in effective for code in self.codes)


def get_user(request: Request) -> User | None:
    user = request.user

    if not user.is_authenticated:
        return None

    return user
