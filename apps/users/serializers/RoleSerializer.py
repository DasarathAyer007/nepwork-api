from typing import Any

from rest_framework import serializers

from apps.users.models import Permission, Role


class RoleSerializer(serializers.ModelSerializer[Role]):
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "code", "name", "description", "permission_codes"]

    def get_permission_codes(self, instance: Role) -> list[str]:
        return sorted(
            instance.role_permissions.values_list("permission__code", flat=True)
        )


class RolePermissionUpdateSerializer(serializers.Serializer):
    permission_codes = serializers.ListField(child=serializers.CharField())

    def validate_permission_codes(self, value: list[str]) -> list[str]:
        existing = set(
            Permission.objects.filter(code__in=value).values_list(
                "code", flat=True
            )
        )
        unknown = set(value) - existing
        if unknown:
            raise serializers.ValidationError(
                f"Unknown permission code(s): {', '.join(sorted(unknown))}."
            )
        return value

    def save(self, **kwargs: Any) -> Role:
        from apps.users.models import RolePermission

        role: Role = self.context["role"]
        codes = self.validated_data["permission_codes"]
        permissions = Permission.objects.filter(code__in=codes)

        RolePermission.objects.filter(role=role).delete()
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in permissions
            ]
        )
        return role
