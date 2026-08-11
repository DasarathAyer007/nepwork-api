from django.contrib.auth.hashers import make_password

from apps.users.models.otp_verification import OTPVerification

from ..tasks import (
    send_account_deletion_otp_task,
    send_change_email_otp_task,
    send_forgot_password_otp_task,
    send_verification_email_task,
)


class OTPService:
    @staticmethod
    def send_signup_otp(user):
        otp = OTPVerification.generate()

        OTPVerification.objects.update_or_create(
            user=user,
            purpose=OTPVerification.Purpose.SIGNUP,
            defaults={
                "otp_hash": make_password(otp),
                "expires_at": OTPVerification.expiry(min=5),
                "new_email": "",
            },
        )

        send_verification_email_task.delay(user.full_name, user.email, otp)

    @staticmethod
    def verify_signup_otp(user, otp):
        email_otp = (
            user.otps.filter(purpose=OTPVerification.Purpose.SIGNUP)
            .order_by("-created_at")
            .first()
        )

        if not email_otp:
            return False

        if email_otp.is_expired():
            return False

        if not email_otp.verify(otp):
            return False

        user.is_active = True

        user.save(
            update_fields=[
                "is_active",
            ]
        )

        email_otp.delete()

        return True

    @staticmethod
    def send_change_email_otp(user, new_email):
        otp = OTPVerification.generate()

        OTPVerification.objects.update_or_create(
            user=user,
            purpose=OTPVerification.Purpose.CHANGE_EMAIL,
            defaults={
                "otp_hash": make_password(otp),
                "expires_at": OTPVerification.expiry(min=10),
                "new_email": new_email,
            },
        )

        send_change_email_otp_task.delay(user.full_name, new_email, otp)

    @staticmethod
    def verify_change_email_otp(user, otp):
        email_otp = (
            user.otps.filter(purpose=OTPVerification.Purpose.CHANGE_EMAIL)
            .order_by("-created_at")
            .first()
        )

        if not email_otp or not email_otp.new_email:
            return None

        if email_otp.is_expired():
            return None

        if not email_otp.verify(otp):
            return None

        new_email = email_otp.new_email

        user.email = new_email
        user.save(update_fields=["email"])

        email_otp.delete()

        return new_email

    @staticmethod
    def send_delete_account_otp(user):
        otp = OTPVerification.generate()

        OTPVerification.objects.update_or_create(
            user=user,
            purpose=OTPVerification.Purpose.DELETE_ACCOUNT,
            defaults={
                "otp_hash": make_password(otp),
                "expires_at": OTPVerification.expiry(min=10),
                "new_email": "",
            },
        )

        send_account_deletion_otp_task.delay(user.full_name, user.email, otp)

    @staticmethod
    def verify_delete_account_otp(user, otp):
        email_otp = (
            user.otps.filter(purpose=OTPVerification.Purpose.DELETE_ACCOUNT)
            .order_by("-created_at")
            .first()
        )

        if not email_otp:
            return False

        if email_otp.is_expired():
            return False

        if not email_otp.verify(otp):
            return False

        email_otp.delete()

        return True

    @staticmethod
    def send_forgot_password_otp(user):
        otp = OTPVerification.generate()

        OTPVerification.objects.update_or_create(
            user=user,
            purpose=OTPVerification.Purpose.FORGOT_PASSWORD,
            defaults={
                "otp_hash": make_password(otp),
                "expires_at": OTPVerification.expiry(min=10),
                "new_email": "",
            },
        )

        send_forgot_password_otp_task.delay(user.full_name, user.email, otp)

    @staticmethod
    def _get_valid_forgot_password_otp(user, otp):
        email_otp = (
            user.otps.filter(purpose=OTPVerification.Purpose.FORGOT_PASSWORD)
            .order_by("-created_at")
            .first()
        )

        if not email_otp or email_otp.is_expired() or not email_otp.verify(otp):
            return None

        return email_otp

    @staticmethod
    def verify_forgot_password_otp(user, otp):
        return OTPService._get_valid_forgot_password_otp(user, otp) is not None

    @staticmethod
    def reset_password_with_otp(user, otp, new_password):
        email_otp = OTPService._get_valid_forgot_password_otp(user, otp)

        if not email_otp:
            return False

        user.set_password(new_password)
        user.save(update_fields=["password"])

        email_otp.delete()

        return True
