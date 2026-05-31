import re

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from apps.users.models.user import User


def validate_password_strength(password: str) -> str:
    if len(password) < 5:
        raise serializers.ValidationError(
            "Password must be at least 5 characters."
        )
    # if not re.search(r'[A-Z]', password):
    #     raise serializers.ValidationError("Password must contain at least one uppercase letter.")
    # if not re.search(r'[a-z]', password):
    #     raise serializers.ValidationError("Password must contain at least one lowercase letter.")
    # if not re.search(r'\d', password):
    #     raise serializers.ValidationError("Password must contain at least one digit.")
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     raise serializers.ValidationError("Password must contain at least one special character.")
    return password


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if not value:
        raise serializers.ValidationError("Email is required.")

    if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", value):
        raise serializers.ValidationError("Enter a valid email address.")

    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError("Email already exists.")

    return value


def validate_username(value: str) -> str:
    value = value.strip()
    if not value:
        raise serializers.ValidationError("Username is required.")

    if len(value) < 3 or len(value) > 30:
        raise serializers.ValidationError(
            "Username must be between 3 and 30 characters."
        )

    if not re.match(r"^[\w.@+-]+$", value):
        raise serializers.ValidationError(
            "Username may contain only letters, digits, and @/./+/-/_ characters."
        )

    if User.objects.filter(username=value).exists():
        raise serializers.ValidationError("Username already exists.")

    return value


def validate_full_name(value: str) -> str:
    value = " ".join(value.split())

    if not value:
        raise serializers.ValidationError("Full name is required.")

    if len(value) < 2:
        raise serializers.ValidationError("Full name is too short.")

    if len(value) > 100:
        raise serializers.ValidationError("Full name is too long.")

    if not re.match(r"^[a-zA-Z\s\.\-]+$", value):
        raise serializers.ValidationError(
            "Full name can only contain letters, spaces, dots, and hyphens."
        )

    return value


def validate_profile_picture(value: UploadedFile | None) -> UploadedFile | None:
    if value is None:
        return value
    max_size = 5 * 1024 * 1024  # 5MB
    if value and value.size is not None and value.size > max_size:
        raise serializers.ValidationError("Profile picture must be under 5MB.")
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if (
        hasattr(value, "content_type")
        and value.content_type not in allowed_types
    ):
        raise serializers.ValidationError(
            "Profile picture must be JPEG, PNG, or WebP."
        )
    return value


def validate_cover_photo(value: UploadedFile | None) -> UploadedFile | None:
    if value is None:
        return value
    max_size = 10 * 1024 * 1024  # 10MB
    if value.size is not None and value.size > max_size:
        raise serializers.ValidationError("Cover photo must be under 10MB.")
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if (
        hasattr(value, "content_type")
        and value.content_type not in allowed_types
    ):
        raise serializers.ValidationError(
            "Cover photo must be JPEG, PNG, or WebP."
        )
    return value


def validate_photo_url(
    value: UploadedFile,
    max_size: int = 5 * 1024 * 1024,
    allowed_types: list[str] | None = None,
) -> UploadedFile | None:
    if allowed_types is None:
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if value is None:
        return value
    if value.size is not None and value.size > max_size:
        raise serializers.ValidationError(
            f"Photo must be under {max_size / (1024 * 1024)}MB."
        )
    if (
        hasattr(value, "content_type")
        and value.content_type not in allowed_types
    ):
        raise serializers.ValidationError(
            f"Photo must be one of the following types: {', '.join(allowed_types)}."
        )

    return value
