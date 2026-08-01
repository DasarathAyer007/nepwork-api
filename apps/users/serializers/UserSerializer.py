import re
from typing import Any

from rest_framework import serializers

from apps.users.rbac import ROLE_RANK
from apps.users.services.permissions import get_role_rank, is_superadmin

from ..models import Role, User
from ..services.user_services import UserService
from .validators import (
    validate_email,
    validate_full_name,
    validate_password_strength,
    validate_username,
)


class UserRegisterSerializer(serializers.ModelSerializer[User]):
    password = serializers.CharField(
        write_only=True,
        min_length=3,
        max_length=128,
    )
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
            "username",
            "password",
            "confirm_password",
            "account_type",
        ]

    def validate_full_name(self, value: str) -> str:
        return validate_full_name(value)

    def validate_email(self, value: str) -> str:
        return validate_email(value)

    def validate_username(self, value: str) -> str:
        return validate_username(value)

    def validate_password(self, value: str) -> str:
        return validate_password_strength(value)

    def validate_account_type(self, value: str) -> str:
        allowed = [User.AccountType.PERSONAL, User.AccountType.ORGANIZATION]
        if value not in allowed:
            raise serializers.ValidationError(
                f"Account type must be one of: {', '.join(allowed)}."
            )
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        data.pop("confirm_password")
        return data

    def create(self, validated_data: dict) -> User:
        """
        Serializer owns the create() call.
        View just calls serializer.save() and reads the result.
        """
        return UserService.register_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            account_type=validated_data["account_type"],
        )


class AdminCreateSerializer(serializers.Serializer):
    """
    Creates a new admin-panel account (User + AdminProfile). Admin accounts
    are never self-registered — this is the only way one gets created, and
    it is always invoked by an already-authenticated admin.
    """

    full_name = serializers.CharField()
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True, min_length=8, max_length=128
    )
    role_code = serializers.CharField()
    department = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    designation = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_email(self, value: str) -> str:
        return validate_email(value)

    def validate_username(self, value: str) -> str:
        return validate_username(value)

    def validate_full_name(self, value: str) -> str:
        return validate_full_name(value)

    def validate_password(self, value: str) -> str:
        return validate_password_strength(value)

    def validate_role_code(self, value: str) -> str:
        if value not in ROLE_RANK:
            raise serializers.ValidationError(f"Unknown role code: {value}.")
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        request = self.context["request"]
        creator = request.user
        target_role_code = data["role_code"]
        creator_is_superadmin = is_superadmin(creator)

        if target_role_code == "superadmin" and not creator_is_superadmin:
            raise serializers.ValidationError(
                {
                    "role_code": "Only a superadmin may create another superadmin."
                }
            )

        if not creator_is_superadmin:
            creator_rank = get_role_rank(creator)
            target_rank = ROLE_RANK[target_role_code]
            if target_rank <= creator_rank:
                raise serializers.ValidationError(
                    {
                        "role_code": "You may only create admin accounts strictly below your own role."
                    }
                )

        return data

    def create(self, validated_data: dict[str, Any]) -> User:
        request = self.context["request"]
        role = Role.objects.get(code=validated_data["role_code"])
        return UserService.create_admin_user(
            full_name=validated_data["full_name"],
            email=validated_data["email"],
            username=validated_data["username"],
            password=validated_data["password"],
            role=role,
            department=validated_data.get("department", ""),
            designation=validated_data.get("designation", ""),
            created_by=request.user,
        )


class AdminUpdateSerializer(serializers.Serializer):
    """
    Updates an existing admin account's role/status/department/designation.
    The requester must already have passed `CanManageAdminUser` (strictly
    senior rank, or superadmin) before this serializer runs.
    """

    role_code = serializers.CharField(required=False)
    status = serializers.ChoiceField(
        choices=User.Status.choices, required=False
    )
    department = serializers.CharField(required=False, allow_blank=True)
    designation = serializers.CharField(required=False, allow_blank=True)

    def validate_role_code(self, value: str) -> str:
        if value not in ROLE_RANK:
            raise serializers.ValidationError(f"Unknown role code: {value}.")
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        target_role_code = data.get("role_code")
        if target_role_code is None:
            return data

        requester = self.context["request"].user
        if target_role_code == "superadmin" and not is_superadmin(requester):
            raise serializers.ValidationError(
                {
                    "role_code": "Only a superadmin may assign the superadmin role."
                }
            )

        if not is_superadmin(requester):
            requester_rank = get_role_rank(requester)
            target_rank = ROLE_RANK[target_role_code]
            if target_rank <= requester_rank:
                raise serializers.ValidationError(
                    {
                        "role_code": "You may only assign roles strictly below your own role."
                    }
                )

        return data

    def update(self, instance, validated_data: dict[str, Any]):
        admin_profile = instance
        user = admin_profile.user

        if "role_code" in validated_data:
            admin_profile.role = Role.objects.get(
                code=validated_data["role_code"]
            )
        if "department" in validated_data:
            admin_profile.department = validated_data["department"]
        if "designation" in validated_data:
            admin_profile.designation = validated_data["designation"]
        admin_profile.save()

        if "status" in validated_data:
            user.status = validated_data["status"]
            user.save(update_fields=["status"])

        return admin_profile


class UpdateUserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["full_name", "username", "profile_picture", "cover_photo"]

    def validate_username(self, value: str) -> str:
        return validate_username(value)

    def validate_full_name(self, value: str) -> str:
        return validate_full_name(value)

    def validate_profile_picture(self, value: str) -> str:
        if value and not re.match(r"^https?://", value):
            raise serializers.ValidationError(
                "Profile picture must be a valid URL."
            )
        return value

    def validate_cover_photo(self, value: str) -> str:
        if value and not re.match(r"^https?://", value):
            raise serializers.ValidationError(
                "Cover photo must be a valid URL."
            )
        return value


class UpdateEmailSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["email"]

    def validate_email(self, value: str) -> str:
        return validate_email(value)


class UpdatePasswordSerializer(serializers.Serializer[User]):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, min_length=8, max_length=128
    )
    confirm_new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value: str) -> str:
        return validate_password_strength(value)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "Passwords do not match."}
            )
        return data
