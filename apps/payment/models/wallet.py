from decimal import Decimal
from uuid import uuid7

from django.core.validators import MinValueValidator
from django.db import models

from apps.utils.models import TimeStampedModel


class Wallet(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="wallet",
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} — {self.balance}"


class LedgerEntry(TimeStampedModel):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"  # increases wallet balance
        DEBIT = "debit", "Debit"  # decreases wallet balance

    class Reason(models.TextChoices):
        SERVICE_EARNING = "service_earning", "Service Earning"
        COMMISSION_FEE = "commission_fee", "Commission Fee"
        PAYOUT = "payout", "Payout"
        REFUND_ADJUSTMENT = "refund_adjustment", "Refund Adjustment"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="entries",
    )

    payment = models.ForeignKey(
        "payment.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ledger_entries",
        help_text="The payment this earning was generated from, if applicable.",
    )

    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
    )

    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Wallet balance immediately after this entry - lets you "
        "reconstruct history without recomputing from scratch.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["reason"]),
        ]

    def __str__(self):
        sign = "+" if self.entry_type == self.EntryType.CREDIT else "-"
        return f"{self.wallet.user} {sign}{self.amount} ({self.reason})"


class Payout(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="payouts",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    method = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. manual, bank_transfer, khalti_transfer - free text for now.",
    )

    note = models.CharField(
        max_length=255,
        blank=True,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payout {self.amount} to {self.wallet.user} ({self.status})"
