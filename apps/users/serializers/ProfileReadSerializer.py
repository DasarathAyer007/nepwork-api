from typing import Any

from rest_framework import serializers

from apps.locations.serializers import LocationSerializer
from apps.skill.serializer import SkillSerializer
from apps.users.models.admin_profile import AdminProfile
from apps.users.models.organization_profile import OrganizationProfile
from apps.users.models.personal_profile import PersonalProfile
from apps.users.models.user import User


class UserSerializer(serializers.ModelSerializer):
    """Declares all user fields. Filtering happens in BaseProfileSerializer."""

    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "full_name",
            "phone_number",
            "profile_picture",
            "cover_photo",
            "bio",
            "date_joined",
            "last_login",
            "social_links",
        )

    def get_profile_picture(self, instance) -> str | None:
        # falls back to the linked social account's avatar (Google/Facebook)
        # when the user hasn't uploaded a profile picture of their own.
        request = self.context.get("request")
        return instance.get_absolute_avatar_url(request)


class BaseProfileSerializer(serializers.ModelSerializer):
    VISIBILITY_FIELDS: dict[str, tuple[str, ...]] = {}

    USER_FIELDS = {
        "full": (
            "id",
            "username",
            "email",
            "full_name",
            "phone_number",
            "profile_picture",
            "cover_photo",
            "bio",
            "date_joined",
            "last_login",
            "location",
            "social_links",
        ),
        "public": (
            "id",
            "username",
            "full_name",
            "profile_picture",
            "cover_photo",
            "bio",
            "location",
            "social_links",
        ),
        "limited": ("id", "username", "full_name", "profile_picture"),
        "private": ("id", "username"),
    }

    def _is_owner(self, instance):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return request.user == instance.user

    def _get_user_data(self, instance, level):
        allowed = self.USER_FIELDS.get(level, self.USER_FIELDS["private"])
        all_user_data = UserSerializer(instance.user, context=self.context).data
        filtered = {k: v for k, v in all_user_data.items() if k in allowed}

        # Inject location separately if allowed
        if "location" in allowed:
            location = getattr(instance.user, "location", None)
            filtered["location"] = (
                LocationSerializer(location, context=self.context).data
                if location
                else None
            )

        return filtered

    def _get_profile_data(self, instance, level):
        allowed = self.VISIBILITY_FIELDS.get(level, ())
        all_profile_data = super().to_representation(instance)
        return {k: v for k, v in all_profile_data.items() if k in allowed}

    def to_representation(self, instance):
        visibility = getattr(
            instance.user,
            "profile_visibility",
            User.ProfileVisibility.PUBLIC,
        )
        level = "full" if self._is_owner(instance) else visibility

        return {
            **self._get_user_data(instance, level),
            **self._get_profile_data(instance, level),
            "access_level": level,
        }


class PersonalProfileSerializer(BaseProfileSerializer):
    VISIBILITY_FIELDS = {
        "public": ("gender", "skills", "interests"),
        "limited": ("gender", "skills"),
        "private": (),
    }
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = PersonalProfile
        fields = (
            "date_of_birth",
            "gender",
            "skills",
            "interests",
        )


class OrganizationProfileSerializer(BaseProfileSerializer):
    VISIBILITY_FIELDS = {
        "public": (
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "is_verified",
        ),
        "limited": ("industry", "logo", "employees_count", "is_verified"),
        "private": (),
    }

    class Meta:
        model = OrganizationProfile
        fields = (
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "tax_id",
            "is_verified",
        )


class AdminProfileReadSerializer(BaseProfileSerializer):
    VISIBILITY_FIELDS = {
        "public": ("role", "department", "designation"),
        "limited": ("role", "department", "designation"),
        "private": (),
    }

    class Meta:
        model = AdminProfile
        fields = [
            "role",
            "ip_address",
            "department",
            "designation",
            "created_by",
            "notes",
        ]


class ProfileReadSerializer(serializers.Serializer):
    """Only entry point. Routes to the correct subclass."""

    serializer: BaseProfileSerializer
    account_type: str

    def to_representation(self, instance) -> dict[str, Any]:
        # instance is always a User object
        account_type = getattr(instance, "account_type", None)

        if account_type == User.AccountType.PERSONAL:
            serializer = PersonalProfileSerializer(
                instance.personal_profile,
                context=self.context,
            )
            account_type = "personal"
        elif account_type == User.AccountType.ORGANIZATION:
            serializer = OrganizationProfileSerializer(
                instance.organization_profile,
                context=self.context,
            )
            account_type = "organization"
        elif account_type == User.AccountType.ADMIN and hasattr(
            instance,
            "admin_profile",
        ):
            serializer = AdminProfileReadSerializer(
                instance.admin_profile,
                context=self.context,
            )
            account_type = "admin"
        else:
            return {"error": "Profile not found for the given user."}

        return {**serializer.data, "account_type": account_type}
