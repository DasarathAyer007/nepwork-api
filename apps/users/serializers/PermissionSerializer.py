from typing import Any

from rest_framework import serializers

from apps.users.models import Permission, User, UserPermission
from apps.users.services.permissions import can_manage_user_permissions


class PermissionSerializer(serializers.ModelSerializer[Permission]):
    resource = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ["id", "code", "name", "description", "resource", "action"]

    def get_resource(self, instance: Permission) -> str:
        return instance.code.rsplit(".", 1)[0]

    def get_action(self, instance: Permission) -> str:
        return instance.code.rsplit(".", 1)[-1]


class UserPermissionSerializer(serializers.ModelSerializer[UserPermission]):
    permission_code = serializers.CharField(
        source="permission.code", read_only=True
    )

    class Meta:
        model = UserPermission
        fields = [
            "id",
            "user",
            "permission",
            "permission_code",
            "is_denied",
            "permission_given_by",
            "created_at",
        ]
        read_only_fields = ["permission_given_by", "created_at"]


class UserPermissionGrantSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    permission_code = serializers.CharField()
    is_denied = serializers.BooleanField(default=False)

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User not found.")
        return value

    def validate_permission_code(self, value: str) -> str:
        if not Permission.objects.filter(code=value).exists():
            raise serializers.ValidationError(
                f"Unknown permission code: {value}."
            )
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        requester = self.context["request"].user
        target = User.objects.get(id=data["user_id"])

        if requester.id == target.id:
            raise serializers.ValidationError(
                {"user_id": "You cannot override your own permissions."}
            )

        if not can_manage_user_permissions(requester, target):
            raise serializers.ValidationError(
                {
                    "user_id": "You may only manage permissions for admins strictly below your own role."
                }
            )

        return data

    def save(self, **kwargs: Any) -> UserPermission:
        granted_by = self.context["request"].user
        permission = Permission.objects.get(
            code=self.validated_data["permission_code"]
        )
        override, _ = UserPermission.objects.update_or_create(
            user_id=self.validated_data["user_id"],
            permission=permission,
            defaults={
                "is_denied": self.validated_data["is_denied"],
                "permission_given_by": granted_by,
            },
        )
        return override
