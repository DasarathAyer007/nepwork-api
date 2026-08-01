from apps.users.models import Permission, User
from apps.users.rbac import ROLE_RANK


def is_superadmin(user: object | None) -> bool:
    """A user is a superadmin if Django's is_superuser flag is set, or if
    their AdminProfile.role is the 'superadmin' role. Centralized so every
    call site (permission classes, serializer validation, rank resolution)
    agrees on the same definition."""
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    profile = getattr(user, "admin_profile", None)
    return bool(
        profile and profile.role_id and profile.role.code == "superadmin"
    )


def get_role_rank(user: object | None) -> int:
    """Lower is more senior. Superadmins (by either definition above) are
    always rank 0. Falls back to the lowest possible rank (len(ROLE_RANK))
    for admin users with no role assigned."""
    if is_superadmin(user):
        return ROLE_RANK["superadmin"]

    profile = getattr(user, "admin_profile", None)
    role_code = profile.role.code if profile and profile.role_id else ""
    return ROLE_RANK.get(role_code, len(ROLE_RANK))


def can_manage_user_permissions(
    requester: object | None, target: object | None
) -> bool:
    """Whether `requester` may grant/deny/revoke a per-user permission
    override belonging to `target`.

    Rules: nobody may override their own permissions (even a superadmin —
    there is no legitimate reason to grant/deny yourself something); a
    superadmin may manage anyone else's; everyone else may only manage a
    target strictly below their own rank (never a peer or senior admin)."""
    if not requester or not target:
        return False

    if getattr(requester, "id", None) == getattr(target, "id", None):
        return False

    if is_superadmin(requester):
        return True

    return get_role_rank(requester) < get_role_rank(target)


def get_effective_permission_codes(user: User | None) -> set[str]:
    """Resolve the full set of permission codes a user currently holds.

    Rule: (role defaults  granted overrides)  denied overrides.
    A Django superuser always gets every permission code, bypassing the
    role/override machinery entirely.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    if user.is_superuser:
        return set(Permission.objects.values_list("code", flat=True))

    admin_profile = getattr(user, "admin_profile", None)
    role_codes: set[str] = set()
    if admin_profile and admin_profile.role_id:
        role_codes = set(
            admin_profile.role.role_permissions.values_list(
                "permission__code", flat=True
            )
        )

    granted = set(
        user.custom_permissions.filter(is_denied=False).values_list(
            "permission__code", flat=True
        )
    )
    denied = set(
        user.custom_permissions.filter(is_denied=True).values_list(
            "permission__code", flat=True
        )
    )

    return (role_codes | granted) - denied
