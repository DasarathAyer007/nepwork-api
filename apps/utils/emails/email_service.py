from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class EmailService:
    @staticmethod
    def send_verification_email(user, otp):
        html = render_to_string(
            "emails/verify_email.html",
            {
                "name": user.full_name,
                "otp": otp,
            },
        )

        email = EmailMultiAlternatives(
            subject="Verify your NepWork account",
            body=f"Your verification code is {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        email.attach_alternative(html, "text/html")

        email.send()
