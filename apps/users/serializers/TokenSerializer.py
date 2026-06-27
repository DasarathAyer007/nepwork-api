from typing import Any

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(attrs)

        user = self.user

        request = self.context.get("request")

        profile_picture_url = None
        if user and user.profile_picture:  # type: ignore[union-attr]
            profile_picture_url = user.profile_picture.url  # type: ignore[union-attr]
            if request:
                profile_picture_url = request.build_absolute_uri(
                    profile_picture_url
                )

        return {
            "access_token": data["access"],
            "refresh_token": data["refresh"],
            "user": {
                "id": user.id,  # type: ignore[union-attr]
                "email": user.email,  # type: ignore[union-attr]
                "username": user.username,  # type: ignore[union-attr]
                "full_name": user.full_name,  # type: ignore[union-attr]
                "account_type": user.account_type,  # type: ignore[union-attr]
                "profile_picture": profile_picture_url,  # type: ignore[union-attr]
                "is_onboarded": user.is_onboarded(),  # type: ignore[union-attr]
            },
        }
