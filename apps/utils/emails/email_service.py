from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class EmailService:
    @staticmethod
    def send_verification_email(full_name, email, otp):
        html = render_to_string(
            "emails/verify_email.html",
            {
                "name": full_name,
                "otp": otp,
            },
        )

        email = EmailMultiAlternatives(
            subject="Verify your NepWork account",
            body=f"Your verification code is {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )

        email.attach_alternative(html, "text/html")

        email.send()

    @staticmethod
    def send_application_status_email(
        applicant, job_title, status_label, message
    ):
        html = render_to_string(
            "emails/application_status_update.html",
            {
                "name": applicant.full_name or applicant.username,
                "job_title": job_title,
                "status_label": status_label,
                "message": message,
            },
        )

        email = EmailMultiAlternatives(
            subject=f"Update on your application for {job_title}",
            body=(
                f"Your application status for {job_title} has been "
                f"updated to {status_label}.\n\n{message}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[applicant.email],
        )

        email.attach_alternative(html, "text/html")

        email.send()
