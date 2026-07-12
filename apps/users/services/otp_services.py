from django.contrib.auth.hashers import make_password

from apps.users.models.otp_verification import OTPVerification

from ..tasks import send_verification_email_task


class OTPService:
    @staticmethod
    def send_signup_otp(user):
        otp = OTPVerification.generate()

        OTPVerification.objects.update_or_create(
            user=user,
            defaults={
                "otp_hash": make_password(otp),
                "expires_at": OTPVerification.expiry(min=5),
            },
        )

        send_verification_email_task.delay(user.full_name, user.email, otp)

    @staticmethod
    def verify_signup_otp(user, otp):
        try:
            email_otp = user.otps.order_by("-created_at").first()
        except OTPVerification.DoesNotExist:
            return False

        if email_otp.is_expired():
            print("OTP expired")
            return False

        if not email_otp.verify(otp):
            print("Invalid OTP")
            return False

        user.is_active = True

        user.save(
            update_fields=[
                "is_active",
            ]
        )

        email_otp.delete()

        return True
