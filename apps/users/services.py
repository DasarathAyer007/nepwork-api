from typing import Any

from apps.users.models.admin_profile import AdminProfile
from apps.users.models.organization_profile import OrganizationProfile
from apps.users.models.personal_profile import PersonalProfile

from .models import User


class UserService:
    @staticmethod
    def create_user(
        full_name: str,
        email: str,
        username: str,
        password: str,
        account_type: str,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            username=username,
            account_type=account_type,
        )

        user.set_password(password)
        user.save()

        return user


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
