# from decimal import Decimal
# from uuid import uuid7

# from django.core.exceptions import ValidationError
# from django.core.validators import MinValueValidator
# from django.db import models

# from apps.utils.models import SoftDeleteModel, TimeStampedModel


# def generate_payment_reference():
#     import uuid

#     return f"NWPAY-{uuid.uuid4().hex[:12].upper()}"


# class PaymentProvider(models.TextChoices):
#     KHALTI = "khalti", "Khalti"
#     ESEWA = "esewa", "eSewa"


# class PaymentStatus(models.TextChoices):
#     PENDING = "pending", "Pending"
#     INITIATED = "initiated", "Initiated"
#     COMPLETED = "completed", "Completed"
#     FAILED = "failed", "Failed"
#     CANCELLED = "cancelled", "Cancelled"
#     PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
#     REFUNDED = "refunded", "Refunded"


# class Payment(TimeStampedModel, SoftDeleteModel):
#     """
#     Represents a payment attempt for a NepWork service request.
#     A service request can have multiple payment attempts.
#     """

#     id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

#     order = models.ForeignKey(
#         "services.ServiceRequest",
#         on_delete=models.PROTECT,
#         related_name="payments",
#     )

#     provider = models.CharField(
#         max_length=20,
#         choices=PaymentProvider.choices,
#     )

#     amount = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         validators=[
#             MinValueValidator(Decimal("0.01")),
#         ],
#     )

#     currency = models.CharField(
#         max_length=3,
#         default="NPR",
#     )

#     verified_amount = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         null=True,
#         blank=True,
#     )

#     refunded_amount = models.DecimalField(
#         max_digits=12,
#         decimal_places=2,
#         default=Decimal("0.00"),
#         validators=[
#             MinValueValidator(Decimal("0.00")),
#         ],
#     )

#     status = models.CharField(
#         max_length=25,
#         choices=PaymentStatus.choices,
#         default=PaymentStatus.PENDING,
#         db_index=True,
#     )

#     reference = models.CharField(
#         max_length=50,
#         unique=True,
#         editable=False,
#         db_index=True,
#         default=generate_payment_reference,
#     )

#     transaction_id = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#         help_text="Internal NepWork transaction identifier.",
#     )

#     provider_transaction_id = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#         help_text="Transaction identifier returned by the payment provider.",
#     )

#     # khalti
#     pidx = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#         help_text="Khalti payment identifier.",
#     )

#     # esewa
#     esewa_transaction_uuid = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#         help_text="Transaction UUID sent to eSewa.",
#     )
#     esewa_ref_id = models.CharField(
#         max_length=255,
#         blank=True,
#         db_index=True,
#         help_text="Reference ID returned by eSewa.",
#     )

#     provider_response = models.JSONField(
#         default=dict,
#         blank=True,
#         help_text="Response received when initiating payment.",
#     )
#     verification_response = models.JSONField(
#         default=dict,
#         blank=True,
#         help_text="Response received when verifying payment.",
#     )

#     failure_reason = models.TextField(
#         blank=True,
#     )

#     refund_reason = models.TextField(
#         blank=True,
#     )

#     initiated_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     completed_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     failed_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     cancelled_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     refunded_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     class Meta:
#         ordering = ["-created_at"]

#         indexes = [
#             models.Index(
#                 fields=["provider", "status"],
#             ),
#             models.Index(
#                 fields=["order", "status"],
#             ),
#             models.Index(
#                 fields=["created_at"],
#             ),
#         ]

#         constraints = [
#             models.UniqueConstraint(
#                 fields=["pidx"],
#                 condition=models.Q(
#                     provider=PaymentProvider.KHALTI,
#                     pidx__gt="",
#                 ),
#                 name="unique_khalti_pidx",
#             ),
#             models.UniqueConstraint(
#                 fields=["esewa_transaction_uuid"],
#                 condition=models.Q(
#                     provider=PaymentProvider.ESEWA,
#                     esewa_transaction_uuid__gt="",
#                 ),
#                 name="unique_esewa_transaction_uuid",
#             ),
#             models.CheckConstraint(
#                 condition=models.Q(
#                     refunded_amount__gte=0,
#                 ),
#                 name="payment_refunded_amount_non_negative",
#             ),
#             models.CheckConstraint(
#                 condition=models.Q(
#                     verified_amount__gte=0,
#                 ),
#                 name="payment_verified_amount_non_negative",
#             ),
#         ]

#     def __str__(self):
#         return f"{self.reference} - {self.amount} {self.currency} "

#     def clean(self):
#         super().clean()

#         if self.refunded_amount > self.amount:
#             raise ValidationError(
#                 {
#                     "refunded_amount": (
#                         "Refunded amount cannot exceed the payment amount."
#                     )
#                 }
#             )

#         if (
#             self.verified_amount is not None
#             and self.verified_amount != self.amount
#         ):
#             raise ValidationError(
#                 {
#                     "verified_amount": (
#                         "Verified amount must match the payment amount."
#                     )
#                 }
#             )

#         if (
#             self.provider == PaymentProvider.KHALTI
#             and self.esewa_transaction_uuid
#         ):
#             raise ValidationError(
#                 {
#                     "esewa_transaction_uuid": (
#                         "eSewa transaction UUID cannot be "
#                         "used for a Khalti payment."
#                     )
#                 }
#             )

#         if self.provider == PaymentProvider.ESEWA and self.pidx:
#             raise ValidationError(
#                 {"pidx": ("Khalti pidx cannot be used for an eSewa payment.")}
#             )

#     @property
#     def is_successful(self):
#         return self.status in {
#             PaymentStatus.COMPLETED,
#             PaymentStatus.PARTIALLY_REFUNDED,
#             PaymentStatus.REFUNDED,
#         }

#     @property
#     def is_refundable(self):
#         return (
#             self.status
#             in {
#                 PaymentStatus.COMPLETED,
#                 PaymentStatus.PARTIALLY_REFUNDED,
#             }
#             and self.refunded_amount < self.amount
#         )

#     @property
#     def remaining_refundable_amount(self):
#         return self.amount - self.refunded_amount
