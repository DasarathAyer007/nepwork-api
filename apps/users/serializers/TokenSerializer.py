from typing import Any

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data = super().validate(attrs)

        user = self.user
        data["account_type"] = user.account_type  # type: ignore[union-attr]
        data["email"] = user.email  # type: ignore[union-attr]
        data["username"] = user.username  # type: ignore[union-attr]

        return data
