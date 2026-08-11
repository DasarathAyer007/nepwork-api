# from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models.user import User

from .validators import validate_password_strength


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")

        return value

    def validate_new_password(self, value):
        # user = self.context["request"].user
        # validate_password(value, user=user)
        return validate_password_strength(value)

    def validate(self, attrs):
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                "New password must be different from the current password."
            )

        return attrs


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        value = value.strip().lower()

        if not User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "No account found with this email address."
            )

        return value


class ForgotPasswordVerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)


class ForgotPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        return validate_password_strength(value)


class RequestEmailChangeSerializer(serializers.Serializer):
    new_email = serializers.EmailField()

    def validate_new_email(self, value):
        user = self.context["request"].user

        if value.lower() == user.email.lower():
            raise serializers.ValidationError(
                "This is already your current email address."
            )

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email address is already in use."
            )

        return value


class ConfirmOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6)
