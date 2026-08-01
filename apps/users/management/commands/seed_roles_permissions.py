from django.core.management.base import BaseCommand

from apps.users.models import Permission, Role, RolePermission
from apps.users.rbac import (
    ACTIONS,
    RESOURCES,
    ROLE_DEFS,
    ROLE_MATRIX,
    permission_code,
)

# python manage.py seed_roles_permissions


class Command(BaseCommand):
    help = "Idempotently seed Permission rows, Role rows, and role-default RolePermission mappings."

    def handle(self, *args, **options):
        permissions: dict[str, Permission] = {}
        for resource in RESOURCES:
            for action in ACTIONS:
                code = permission_code(resource, action)
                permission, created = Permission.objects.get_or_create(
                    code=code,
                    defaults={
                        "name": code.replace(".", " ")
                        .replace("_", " ")
                        .title(),
                        "description": f"Can {action} {resource}",
                    },
                )
                permissions[code] = permission
                if created:
                    self.stdout.write(f"  + permission {code}")

        for role_code, role_name in ROLE_DEFS.items():
            role, created = Role.objects.get_or_create(
                code=role_code, defaults={"name": role_name}
            )
            if created:
                self.stdout.write(f"  + role {role_code}")

            for resource, actions in ROLE_MATRIX[role_code].items():
                for action in actions:
                    code = permission_code(resource, action)
                    _, created = RolePermission.objects.get_or_create(
                        role=role, permission=permissions[code]
                    )
                    if created:
                        self.stdout.write(f"  + {role_code} -> {code}")

        self.stdout.write(self.style.SUCCESS("Roles and permissions seeded."))
