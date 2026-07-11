from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User

# from .services.user_services import UserService


class RegisterSerializer(serializers.ModelSerializer[User]):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["full_name", "email", "username", "password", "account_type"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_username(self, value: str) -> str:
        return value.strip()

    def validate_password(self, value: str) -> str:
        if len(value) < 3:
            raise serializers.ValidationError(
                "Password must be at least 3 characters"
            )
        return value

    # def create(self, validated_data: dict[str, Any]) -> User:
    #     return UserService.register_user(**validated_data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        data = super().validate(attrs)

        user = self.user
        data["account_type"] = user.account_type  # type: ignore[union-attr]
        data["email"] = user.email  # type: ignore[union-attr]
        data["username"] = user.username  # type: ignore[union-attr]

        return data
