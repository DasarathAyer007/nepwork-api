from celery import shared_task

from apps.utils.emails.email_service import EmailService


@shared_task(ignore_result=True)
def send_verification_email_task(full_name: str, email: str, otp: str) -> None:
    EmailService.send_verification_email(
        full_name=full_name,
        email=email,
        otp=otp,
    )
    print(f"Sent verification email to {email} with OTP: {otp}")
