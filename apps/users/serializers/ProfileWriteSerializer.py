from datetime import date

from django.core.files.uploadedfile import UploadedFile
from django.core.validators import URLValidator
from jsonschema import ValidationError
from rest_framework import serializers

from apps.users.models.organization_profile import OrganizationProfile
from apps.users.models.personal_profile import PersonalProfile


class PersonalProfileWriteSerializer(
    serializers.ModelSerializer[PersonalProfile]
):
    class Meta:
        model = PersonalProfile
        fields = [
            "id",
            "bio",
            "date_of_birth",
            "gender",
            "skills",
            "interests",
            "profile_visibility",
            "social_links",
        ]

        read_only_fields = ["id"]

    def validate_date_of_birth(self, value: date) -> date:
        if value and value > date.today():
            raise serializers.ValidationError(
                "Date of birth cannot be in the future."
            )
        return value

    def validate_skills(self, value: dict[str, str]) -> dict[str, str]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Skills must be a dictionary.")
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip():
                raise serializers.ValidationError(
                    "Each skill key must be a non-empty string."
                )
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError(
                    "Each skill value must be a non-empty string."
                )
        return value

    def validate_interests(self, value: dict[str, str]) -> dict[str, str]:
        # same as skills
        if not isinstance(value, dict):
            raise serializers.ValidationError("Interests must be a dictionary.")
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip():
                raise serializers.ValidationError(
                    "Each interest key must be a non-empty string."
                )
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError(
                    "Each interest value must be a non-empty string."
                )
        return value

    def validate_social_links(self, value: dict[str, str]) -> dict[str, str]:
        # if not isinstance(value, dict):
        #     raise serializers.ValidationError(
        #         "Social links must be a dictionary."
        #     )
        # url_validator = URLValidator()
        # for platform, url in value.items():
        #     if not isinstance(platform, str) or not isinstance(url, str):
        #         raise serializers.ValidationError("Invalid social link format.")
        #     try:
        #         url_validator(url)
        #     except ValidationError:
        #         raise serializers.ValidationError(
        #             f"Invalid URL for {platform}."
        #         )
        return value


class OrganizationProfileWriteSerializer(
    serializers.ModelSerializer[OrganizationProfile]
):
    class Meta:
        model = OrganizationProfile
        fields = [
            "id",
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
        read_only_fields = ["id", "is_verified"]

    def validate_organization_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Organization name is required.")
        if len(value) > 50:
            raise serializers.ValidationError(
                "Organization name must be 50 characters or less."
            )
        return value.strip()

    def validate_employees_count(self, value: int) -> int:
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Employee count must be a positive integer."
            )
        return value

    def validate_founded_at(self, value: date) -> date:
        if value and value > date.today():
            raise serializers.ValidationError(
                "Founded date cannot be in the future."
            )
        return value

    def validate_social_links(self, value: dict[str, str]) -> dict[str, str]:
        # same as personal profile
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Social links must be a dictionary."
            )
        url_validator = URLValidator()
        for platform, url in value.items():
            if not isinstance(platform, str) or not isinstance(url, str):
                raise serializers.ValidationError("Invalid social link format.")
            try:
                url_validator(url)
            except ValidationError:
                raise serializers.ValidationError(
                    f"Invalid URL for {platform}."
                )
        return value

    def validate_logo(self, value: UploadedFile | None) -> UploadedFile | None:
        if value is None:
            return value
        # Example file size and type check
        max_size = 2 * 1024 * 1024  # 2MB
        if value.size is not None and value.size > max_size:
            raise serializers.ValidationError(
                "Logo file size must be under 2MB."
            )
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if (
            hasattr(value, "content_type")
            and value.content_type not in allowed_types
        ):
            raise serializers.ValidationError(
                "Logo must be JPEG, PNG, or WebP."
            )
        return value
