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
    is_onboarded = serializers.SerializerMethodField()

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
            "is_onboarded",
        )

    def get_profile_picture(self, instance) -> str | None:
        # falls back to the linked social account's avatar (Google/Facebook)
        # when the user hasn't uploaded a profile picture of their own.
        request = self.context.get("request")
        return instance.get_absolute_avatar_url(request)

    def get_is_onboarded(self, instance) -> bool:
        return instance.is_onboarded()


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
            "is_onboarded",
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
            "is_onboarded",
        ),
        "limited": (
            "id",
            "username",
            "full_name",
            "profile_picture",
            "is_onboarded",
        ),
        "private": (
            "id",
            "username",
            "profile_picture",
            "cover_photo",
            "bio",
            "is_onboarded",
        ),
    }

    def _is_owner(self, instance):
        request = self.context.get("request")

        if request is None:
            return False

        if not hasattr(request, "user"):
            return False

        if not request.user.is_authenticated:
            return False

        return str(request.user.id) == str(instance.user.id)

    def _get_user_data(self, instance, level):
        allowed = self.USER_FIELDS.get(level, self.USER_FIELDS["full"])
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
        is_owner = self._is_owner(instance)

        visibility = getattr(
            instance.user,
            "profile_visibility",
            User.ProfileVisibility.PUBLIC,
        )

        level = "full" if is_owner else visibility

        return {
            **self._get_user_data(instance, level),
            **self._get_profile_data(instance, level),
            "access_level": level,
        }


class PersonalProfileSerializer(BaseProfileSerializer):
    VISIBILITY_FIELDS = {
        "full": (
            "age",
            "gender",
            "skills",
            "interests",
        ),
        "public": (
            "age",
            "gender",
            "skills",
            "interests",
        ),
        "limited": (
            "age",
            "gender",
            "skills",
            "interests",
        ),
        "private": (),
    }
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = PersonalProfile
        fields = (
            "age",
            "gender",
            "skills",
            "interests",
        )


class OrganizationProfileSerializer(BaseProfileSerializer):
    VISIBILITY_FIELDS = {
        "full": (
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "tax_id",
            "is_verified",
        ),
        "public": (
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "is_verified",
        ),
        "limited": (
            "industry",
            "logo",
            "employees_count",
            "is_verified",
        ),
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
        "full": ("role", "ip_address", "department", "designation", "notes"),
        "public": ("role", "department", "designation"),
        "limited": ("role", "department", "designation"),
        "private": (),
    }

    role = serializers.SerializerMethodField()

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

    def get_role(self, instance) -> dict[str, str] | None:
        if not instance.role_id:
            return None
        return {"code": instance.role.code, "name": instance.role.name}


class ProfileReadSerializer(serializers.Serializer):
    """Only entry point. Routes to the correct subclass."""

    serializer: BaseProfileSerializer
    account_type: str

    def to_representation(self, instance) -> dict[str, Any]:
        # instance is always a User object
        account_type = getattr(instance, "account_type", None)

        if account_type == User.AccountType.PERSONAL:
            if not hasattr(instance, "personal_profile"):
                return self._not_onboarded(instance, "personal")

            serializer = PersonalProfileSerializer(
                instance.personal_profile,
                context=self.context,
            )
            account_type = "personal"
        elif account_type == User.AccountType.ORGANIZATION:
            if not hasattr(instance, "organization_profile"):
                return self._not_onboarded(instance, "organization")

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

    def _not_onboarded(self, instance, account_type: str) -> dict[str, Any]:
        return {
            "is_onboarded": False,
            "account_type": account_type,
            "user": UserSerializer(instance, context=self.context).data,
        }
