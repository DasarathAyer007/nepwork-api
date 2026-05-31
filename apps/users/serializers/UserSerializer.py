import re
from typing import Any

from rest_framework import serializers

from ..models import User
from ..services import UserService
from .validators import (
    validate_email,
    validate_full_name,
    validate_password_strength,
    validate_username,
)


class UserRegisterSerializer(serializers.ModelSerializer[User]):
    password = serializers.CharField(
        write_only=True, min_length=8, max_length=128
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
        if value not in [
            User.AccountType.PERSONAL,
            User.AccountType.ORGANIZATION,
        ]:
            raise serializers.ValidationError("Invalid account type.")
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return data

    def create(self, validated_data: dict[str, Any]) -> User:
        validated_data.pop("confirm_password")
        return UserService.create_user(**validated_data)


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
