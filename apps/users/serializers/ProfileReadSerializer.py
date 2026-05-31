from typing import Any

from rest_framework import serializers

from apps.users.models.admin_profile import AdminProfile
from apps.users.models.organization_profile import OrganizationProfile
from apps.users.models.personal_profile import PersonalProfile
from apps.users.models.user import User

# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = User
#         fields = [
#             "id",
#             "full_name",
#             "username",
#             "email",
#             "phone_number",
#             "account_type",
#             "profile_picture",
#             "cover_photo",
#             "status",
#         ]


# class PersonalProfileReadSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)

#     class Meta:
#         model = PersonalProfile
#         fields = [
#             "user",
#             "bio",
#             "date_of_birth",
#             "gender",
#             "skills",
#             "interests",
#             "profile_visibility",
#             "social_links",
#         ]


# class OrganizationProfileReadSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)

#     class Meta:
#         model = OrganizationProfile
#         fields = [
#             "user",
#             "organization_name",
#             "description",
#             "industry",
#             "logo",
#             "employees_count",
#             "founded_at",
#             "address",
#             "tax_id",
#             "social_links",
#             "is_verified",
#         ]

#     def to_representation(self, instance):
#         data = super().to_representation(instance)

#         profile_fields = {
#            "organization_name": data['organization_name'],
#            "description": data['description'],
#            "industry": data['industry'],
#            "logo": data['logo'],
#            "employees_count": data['employees_count'],
#            "founded_at": data['founded_at'],
#            "address": data['address'],
#            "tax_id": data['tax_id'],
#         }

#         return {
#             "user": data['user'],
#             "profile": profile_fields
#         }


# class AdminProfileReadSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)

#     class Meta:
#         model = PersonalProfile
#         fields = ["user", "bio", "date_of_birth", "gender"]


class BaseProfileResponseSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    def to_representation(self, instance: Any) -> dict[str, Any]:
        data = super().to_representation(instance)

        user = data.pop("user")

        return {
            "user": user,
            "profile": data,
        }


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "username",
            "email",
            "phone_number",
            "account_type",
            "profile_picture",
            "cover_photo",
            "status",
        ]


class PersonalProfileReadSerializer(BaseProfileResponseSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = PersonalProfile
        fields = [
            "user",
            "bio",
            "date_of_birth",
            "gender",
            "skills",
            "interests",
            "profile_visibility",
            "social_links",
        ]


class OrganizationProfileReadSerializer(BaseProfileResponseSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = OrganizationProfile
        fields = [
            "user",
            "organization_name",
            "description",
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "tax_id",
            "social_links",
            "is_verified",
        ]


class AdminProfileReadSerializer(BaseProfileResponseSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = AdminProfile
        fields = [
            "user",
            "role",
            "ip_address",
            "department",
            "designation",
            "notes",
        ]
