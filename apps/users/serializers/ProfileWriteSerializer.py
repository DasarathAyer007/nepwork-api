import json
from datetime import date

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from rest_framework import serializers

from apps.skill.services import SkillService
from apps.users.models.organization_profile import OrganizationProfile
from apps.users.models.personal_profile import PersonalProfile
from apps.users.models.user import User


class FutureDateMixin:
    def _reject_future(
        self,
        value: date,
        field_label: str,
    ) -> date:
        if value and value > date.today():
            raise serializers.ValidationError(
                f"{field_label} cannot be in the future."
            )
        return value


class ImageUploadMixin:
    MAX_SIZE_MB = 5
    ALLOWED_TYPES = [
        "image/jpeg",
        "image/png",
        "image/webp",
    ]

    def _validate_image(
        self,
        value: UploadedFile | None,
    ) -> UploadedFile | None:
        if value is None:
            return value

        if value.size and value.size > self.MAX_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"Image must be under {self.MAX_SIZE_MB}MB."
            )

        if getattr(value, "content_type", None) not in self.ALLOWED_TYPES:
            raise serializers.ValidationError(
                "Image must be JPEG, PNG, or WebP."
            )

        return value


class BaseProfileWriteSerializer(
    FutureDateMixin,
    ImageUploadMixin,
    serializers.ModelSerializer,
):
    bio = serializers.CharField(
        required=False,
        max_length=500,
        trim_whitespace=True,
        write_only=True,
    )

    profile_visibility = serializers.ChoiceField(
        choices=User.ProfileVisibility.choices,
        required=False,
        write_only=True,
    )

    profile_picture = serializers.ImageField(
        required=False,
        write_only=True,
        allow_null=True,
    )

    cover_photo = serializers.ImageField(
        required=False,
        write_only=True,
        allow_null=True,
    )

    # social_links = serializers.DictField(
    #     child=serializers.URLField(),
    #     required=False,
    #     default=dict,
    #     write_only=True,
    # )

    social_links = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=dict,
        write_only=True,
    )

    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )

    def to_internal_value(self, data):
        if hasattr(data, "dict"):
            mutable_data = {}

            for key in data:
                values = data.getlist(key)

                # preserve multiple values like skills
                if len(values) > 1:
                    mutable_data[key] = values
                else:
                    mutable_data[key] = values[0]

            # keep uploaded files
            if hasattr(data, "FILES"):
                for key, file in data.FILES.items():
                    mutable_data[key] = file

            data = mutable_data

        social_links = data.get("social_links")

        if isinstance(social_links, str):
            try:
                data["social_links"] = json.loads(social_links)
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    {"social_links": "Invalid JSON format."}
                )

        return super().to_internal_value(data)

    def validate_bio(
        self,
        value: str,
    ) -> str:
        if not value.strip():
            raise serializers.ValidationError("Bio cannot be blank.")
        return value.strip()

    def validate_profile_picture(self, value):
        return self._validate_image(value)

    def validate_cover_photo(self, value):
        return self._validate_image(value)

    def validate_social_links(
        self,
        value: dict,
    ) -> dict:
        invalid_keys = [
            k for k in value if not k.strip() or not k.islower() or " " in k
        ]

        if invalid_keys:
            raise serializers.ValidationError(
                f"Platform names must be lowercase with no spaces: {invalid_keys}"
            )

        return {k.strip(): v for k, v in value.items()}

    def _pop_user_fields(
        self,
        validated_data: dict,
        user=None,
    ):
        if user is None:
            user = getattr(
                self.instance,
                "user",
                None,
            )

        if user is None:
            user = validated_data.pop(
                "user",
                None,
            )

        if user is None:
            raise serializers.ValidationError(
                {"user": "User instance not found."}
            )

        bio = validated_data.pop(
            "bio",
            None,
        )

        profile_visibility = validated_data.pop(
            "profile_visibility",
            None,
        )

        profile_picture = validated_data.pop(
            "profile_picture",
            None,
        )

        cover_photo = validated_data.pop(
            "cover_photo",
            None,
        )

        social_links = validated_data.pop(
            "social_links",
            None,
        )

        phone_number = validated_data.pop(
            "phone_number",
            None,
        )

        user_updates = {}

        if bio is not None:
            user_updates["bio"] = bio

        if profile_visibility is not None:
            user_updates["profile_visibility"] = profile_visibility

        if profile_picture is not None:
            user_updates["profile_picture"] = profile_picture

        if cover_photo is not None:
            user_updates["cover_photo"] = cover_photo

        if social_links is not None:
            user_updates["social_links"] = social_links

        if phone_number is not None:
            user_updates["phone_number"] = phone_number

        print("USER UPDATES:")
        print(user_updates)

        if user_updates:
            for attr, value in user_updates.items():
                setattr(
                    user,
                    attr,
                    value,
                )

            user.save(update_fields=list(user_updates.keys()))

            user.refresh_from_db()

            print(
                "AFTER DB SAVE:",
                user.social_links,
            )

        return user

    def _apply_update(
        self,
        instance,
        validated_data: dict,
    ):
        self._pop_user_fields(
            validated_data,
            user=instance.user,
        )

        for attr, value in validated_data.items():
            setattr(
                instance,
                attr,
                value,
            )

        instance.save()
        return instance


class PersonalProfileWriteSerializer(BaseProfileWriteSerializer):
    skills = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True),
        required=False,
        write_only=True,
    )

    interests = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True),
        required=False,
        allow_null=True,
    )

    gender = serializers.ChoiceField(
        choices=PersonalProfile.Gender.choices,
        required=False,
    )

    date_of_birth = serializers.DateField(required=False)

    class Meta:
        model = PersonalProfile
        fields = [
            "id",
            "bio",
            "phone_number",
            "profile_visibility",
            "profile_picture",
            "cover_photo",
            "social_links",
            "date_of_birth",
            "gender",
            "skills",
            "interests",
        ]
        read_only_fields = ["id"]

    def validate_date_of_birth(
        self,
        value: date,
    ) -> date:
        return self._reject_future(
            value,
            "Date of birth",
        )

    def validate_skills(
        self,
        value: list,
    ) -> list:
        if not value:
            return []

        cleaned = []
        seen = set()

        for skill in value:
            normalized = skill.strip().lower()

            if not normalized or normalized in seen:
                continue

            seen.add(normalized)
            cleaned.append(normalized)

        return cleaned

    def validate_interests(
        self,
        value: list,
    ) -> list:
        if not value:
            return []

        return [
            interest.strip().lower() for interest in value if interest.strip()
        ]

    @transaction.atomic
    def create(
        self,
        validated_data: dict,
    ) -> PersonalProfile:
        skills_data = validated_data.pop("skills", [])

        user = self.context["request"].user

        self._pop_user_fields(
            validated_data,
            user=user,
        )

        profile, _ = PersonalProfile.objects.update_or_create(
            user=user,
            defaults=validated_data,
        )

        if skills_data:
            profile.skills.set(SkillService.get_or_create_skills(skills_data))

        return profile

    @transaction.atomic
    def update(
        self,
        instance: PersonalProfile,
        validated_data: dict,
    ) -> PersonalProfile:
        skills_data = validated_data.pop(
            "skills",
            None,
        )

        instance = self._apply_update(
            instance,
            validated_data,
        )

        if skills_data is not None:
            instance.skills.set(SkillService.get_or_create_skills(skills_data))

        return instance


class OrganizationProfileWriteSerializer(BaseProfileWriteSerializer):
    industry = serializers.CharField(
        required=False,
        trim_whitespace=True,
        allow_blank=True,
    )

    logo = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    employees_count = serializers.IntegerField(
        required=False,
        min_value=1,
    )

    founded_at = serializers.DateField(
        required=False,
        allow_null=True,
    )

    address = serializers.CharField(
        required=False,
        trim_whitespace=True,
        allow_blank=True,
    )

    tax_id = serializers.CharField(
        required=False,
        min_length=5,
        max_length=50,
        trim_whitespace=True,
        allow_blank=True,
    )

    class Meta:
        model = OrganizationProfile
        fields = [
            "id",
            "bio",
            "phone_number",
            "profile_visibility",
            "profile_picture",
            "cover_photo",
            "social_links",
            "industry",
            "logo",
            "employees_count",
            "founded_at",
            "address",
            "tax_id",
            "is_verified",
        ]
        read_only_fields = [
            "id",
            "is_verified",
        ]

    def validate_logo(self, value):
        return self._validate_image(value)

    def validate_founded_at(
        self,
        value: date,
    ) -> date:
        return self._reject_future(
            value,
            "Founded date",
        )

    def validate_tax_id(
        self,
        value: str,
    ) -> str:
        if value and not value.isalnum():
            raise serializers.ValidationError(
                "Tax ID must contain only letters and numbers."
            )

        return value.upper()

    @transaction.atomic
    def create(
        self,
        validated_data: dict,
    ) -> OrganizationProfile:
        user = self.context["request"].user

        self._pop_user_fields(
            validated_data,
            user=user,
        )

        profile, _ = OrganizationProfile.objects.update_or_create(
            user=user,
            defaults=validated_data,
        )

        return profile

    @transaction.atomic
    def update(
        self,
        instance: OrganizationProfile,
        validated_data: dict,
    ) -> OrganizationProfile:
        return self._apply_update(
            instance,
            validated_data,
        )
