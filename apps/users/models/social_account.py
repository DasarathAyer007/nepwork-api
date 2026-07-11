from django.db import models

from apps.utils.models import TimeStampedModel

from .user import User


class SocialAccount(TimeStampedModel):
    PROVIDER_CHOICES = [
        ("google", "Google"),
        ("facebook", "Facebook"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="social_accounts",
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_id = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    avatar_url = models.URLField(blank=True)
    extra_data = models.JSONField(blank=True, null=True)

    class Meta:
        unique_together = ("provider", "provider_id")
        indexes = [
            models.Index(fields=["provider", "provider_id"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_id} -> user_id={self.user_id}"
