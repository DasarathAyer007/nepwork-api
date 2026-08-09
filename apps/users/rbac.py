"""Central constants for the role-based permission system.

Single source of truth for resource/action codes, per-role default
permission matrix, and role ranking (used to gate admin creation).
"""

RESOURCES = [
    "users",
    "jobs",
    "services",
    "skills",
    "communication",
    "roles",
    "permissions",
    "settings",
    "audit_logs",
    "sliding_images",
    "analytics",
    "reviews",
]

ACTIONS = ["view", "edit", "delete"]

ROLE_DEFS = {
    "superadmin": "Super Admin",
    "admin": "Admin",
    "moderator": "Moderator",
    "developer": "Developer",
}

ROLE_RANK = {
    "superadmin": 0,
    "admin": 1,
    "moderator": 2,
    "developer": 2,
}

_ALL_ACTIONS = set(ACTIONS)
_VIEW_EDIT = {"view", "edit"}
_VIEW_ONLY = {"view"}

ROLE_MATRIX: dict[str, dict[str, set[str]]] = {
    "superadmin": {resource: set(_ALL_ACTIONS) for resource in RESOURCES},
    "admin": {
        "users": set(_ALL_ACTIONS),
        "jobs": set(_ALL_ACTIONS),
        "services": set(_ALL_ACTIONS),
        "skills": set(_ALL_ACTIONS),
        "communication": set(_ALL_ACTIONS),
        "roles": set(_VIEW_ONLY),
        "permissions": set(_VIEW_EDIT),
        "settings": set(_ALL_ACTIONS),
        "audit_logs": set(_ALL_ACTIONS),
        "sliding_images": set(_ALL_ACTIONS),
        "analytics": set(_VIEW_ONLY),
        "reviews": set(_ALL_ACTIONS),
    },
    "moderator": {
        "users": set(),
        "jobs": set(_VIEW_EDIT),
        "services": set(_VIEW_EDIT),
        "skills": set(_VIEW_EDIT),
        "communication": set(_VIEW_EDIT),
        "roles": set(),
        "permissions": set(),
        "settings": set(),
        "audit_logs": set(),
        "sliding_images": set(_VIEW_ONLY),
        "analytics": set(_VIEW_ONLY),
        "reviews": set(_ALL_ACTIONS),
    },
    "developer": {resource: set(_VIEW_ONLY) for resource in RESOURCES},
}


def permission_code(resource: str, action: str) -> str:
    return f"{resource}.{action}"
