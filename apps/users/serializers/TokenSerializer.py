from typing import Any

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(attrs)

        data["access_token"] = data.pop("access")
        if "refresh" in data:
            data["refresh_token"] = data.pop("refresh")

        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def build_response_data(cls, user, request=None):
        refresh = RefreshToken.for_user(user)

        profile_picture_url = (
            user.get_absolute_avatar_url(request) if user else None  # type: ignore[union-attr]
        )

        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "id": user.id,  # type: ignore[union-attr]
                "email": user.email,  # type: ignore[union-attr]
                "username": user.username,  # type: ignore[union-attr]
                "full_name": user.full_name,  # type: ignore[union-attr]
                "account_type": user.account_type,  # type: ignore[union-attr]
                "profile_picture": profile_picture_url,
                "is_onboarded": user.is_onboarded(),  # type: ignore[union-attr]
            },
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        super().validate(attrs)

        user = self.user
        request = self.context.get("request")

        return self.build_response_data(user, request)
