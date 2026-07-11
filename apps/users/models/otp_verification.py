import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.db import models
from django.utils import timezone

from .user import User


class OTPVerification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otps",
    )

    otp_hash = models.CharField(max_length=255)

    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(default=0)

    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    @classmethod
    def generate(cls):
        return f"{secrets.randbelow(1_000_000):06}"

    @classmethod
    def expiry(cls, min=10):
        return timezone.now() + timedelta(minutes=min)

    def verify(self, otp):
        print(f"Verifying OTP: {otp} against hash: {self.otp_hash}")
        return check_password(otp, self.otp_hash)
