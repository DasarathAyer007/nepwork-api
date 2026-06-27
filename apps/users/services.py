from typing import Any

from django.db import transaction

from apps.users.models.admin_profile import AdminProfile
from apps.users.models.organization_profile import OrganizationProfile
from apps.users.models.personal_profile import PersonalProfile

from .models import User

DEFAULT_PROFILE_PICTURE_URL = "profile_pictures/default.jpg"
DEFAULT_COVER_PHOTO_URL = "cover_photos/default.jpg"


class UserService:
    @staticmethod
    @transaction.atomic
    def register_user(
        full_name: str,
        email: str,
        username: str,
        password: str,
        account_type: str,
    ) -> User:
        # 1. Create the user
        user = User(
            full_name=full_name,
            email=email,
            username=username,
            account_type=account_type,
            profile_picture=DEFAULT_PROFILE_PICTURE_URL,
            cover_photo=DEFAULT_COVER_PHOTO_URL,
        )
        user.set_password(password)
        user.save()

        # 2. Create the matching empty profile
        UserService._create_default_profile(user)

        return user

    @staticmethod
    def _create_default_profile(user: User) -> None:
        """Creates an empty profile record based on account_type."""
        if user.account_type == User.AccountType.PERSONAL:
            PersonalProfile.objects.create(
                user=user,
                date_of_birth=None,
                interests=[],
            )

        elif user.account_type == User.AccountType.ORGANIZATION:
            OrganizationProfile.objects.create(
                user=user,
                employees_count=None,
                founded_at=None,
                address="",
                tax_id="",
                is_verified=False,
            )


class ProfileService:
    @staticmethod
    def create_personal_profile(
        user: User, validated_data: dict[str, Any]
    ) -> PersonalProfile:
        return PersonalProfile.objects.create(user=user, **validated_data)

    @staticmethod
    def update_personal_profile(
        profile: PersonalProfile, validated_data: dict[str, Any]
    ) -> PersonalProfile:
        for attr, value in validated_data.items():
            setattr(profile, attr, value)

        profile.save()
        return profile

    @staticmethod
    def create_profile(
        user: User, validated_data: dict[str, Any]
    ) -> PersonalProfile | OrganizationProfile | AdminProfile | None:
        if user.account_type == User.AccountType.PERSONAL:
            return PersonalProfile.objects.create(user=user, **validated_data)

        if user.account_type == User.AccountType.ORGANIZATION:
            return OrganizationProfile.objects.create(
                user=user, **validated_data
            )

        if user.account_type == User.AccountType.ADMIN:
            return AdminProfile.objects.create(user=user, **validated_data)

        return None

    @staticmethod
    def get_profile(
        user: User,
    ) -> PersonalProfile | OrganizationProfile | AdminProfile | None:
        if user.account_type == User.AccountType.PERSONAL:
            return PersonalProfile.objects.filter(user=user).first()

        if user.account_type == User.AccountType.ORGANIZATION:
            return OrganizationProfile.objects.filter(user=user).first()

        if user.account_type == User.AccountType.ADMIN:
            return AdminProfile.objects.filter(user=user).first()

        return None

    @staticmethod
    def check_profile_exists(user: User) -> bool:
        if user.account_type == User.AccountType.PERSONAL:
            return PersonalProfile.objects.filter(user=user).exists()

        if user.account_type == User.AccountType.ORGANIZATION:
            return OrganizationProfile.objects.filter(user=user).exists()

        if user.account_type == User.AccountType.ADMIN:
            return AdminProfile.objects.filter(user=user).exists()

        return False
