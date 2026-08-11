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


@shared_task(ignore_result=True)
def send_change_email_otp_task(
    full_name: str, new_email: str, otp: str
) -> None:
    EmailService.send_change_email_otp(
        full_name=full_name,
        new_email=new_email,
        otp=otp,
    )
    print(f"Sent change-email OTP to {new_email} with OTP: {otp}")


@shared_task(ignore_result=True)
def send_account_deletion_otp_task(
    full_name: str, email: str, otp: str
) -> None:
    EmailService.send_account_deletion_otp(
        full_name=full_name,
        email=email,
        otp=otp,
    )
    print(f"Sent account-deletion OTP to {email} with OTP: {otp}")


@shared_task(ignore_result=True)
def send_forgot_password_otp_task(full_name: str, email: str, otp: str) -> None:
    EmailService.send_forgot_password_otp(
        full_name=full_name,
        email=email,
        otp=otp,
    )
    print(f"Sent forgot-password OTP to {email} with OTP: {otp}")
