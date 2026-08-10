from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.payment.services.khalti_service import (
    KhaltiGateway,
    KhaltiGatewayError,
)

from ..models import Payment
from .wallet_services import WalletService

VALID_TRANSITIONS = {
    Payment.PaymentStatus.PENDING: {
        Payment.PaymentStatus.INITIATED,
        Payment.PaymentStatus.FAILED,
        Payment.PaymentStatus.CANCELLED,
    },
    Payment.PaymentStatus.INITIATED: {
        Payment.PaymentStatus.COMPLETED,
        Payment.PaymentStatus.FAILED,
        Payment.PaymentStatus.CANCELLED,
    },
    Payment.PaymentStatus.COMPLETED: {
        Payment.PaymentStatus.PARTIALLY_REFUNDED,
        Payment.PaymentStatus.REFUNDED,
    },
    Payment.PaymentStatus.PARTIALLY_REFUNDED: {
        Payment.PaymentStatus.PARTIALLY_REFUNDED,
        Payment.PaymentStatus.REFUNDED,
    },
    Payment.PaymentStatus.FAILED: set(),
    Payment.PaymentStatus.CANCELLED: set(),
    Payment.PaymentStatus.REFUNDED: set(),
}

VERIFICATION_BACKOFF_SECONDS = [30, 120, 300, 600, 1800, 3600]
MAX_VERIFICATION_ATTEMPTS = 10


class PaymentService:
    @staticmethod
    def _transition(
        payment,
        new_status,
        timestamp_field=None,
        **extra,
    ):
        allowed_statuses = VALID_TRANSITIONS.get(
            payment.status,
            set(),
        )

        if new_status not in allowed_statuses:
            raise ValidationError(
                f"Cannot transition payment from "
                f"'{payment.status}' to '{new_status}'."
            )

        payment.status = new_status

        if timestamp_field:
            setattr(
                payment,
                timestamp_field,
                timezone.now(),
            )

        for field, value in extra.items():
            setattr(payment, field, value)

        payment.save()

        return payment

    @staticmethod
    @transaction.atomic
    def create_payment(
        order,
        provider,
        amount,
        currency="NPR",
    ):
        return Payment.objects.create(
            order=order,
            provider=provider,
            amount=amount,
            currency=currency,
        )

    @staticmethod
    def initiate_khalti_payment(order, amount, user_info, return_url=None):
        payment = PaymentService.create_payment(
            order=order,
            provider=Payment.PaymentProvider.KHALTI,
            amount=amount,
        )

        gateway = KhaltiGateway()

        try:
            provider_response = gateway.initiate(
                payment, user_info, return_url=return_url
            )
        except KhaltiGatewayError as exc:
            PaymentService.fail(payment, reason=str(exc))
            raise

        payment = PaymentService.initiate(
            payment,
            provider_response=provider_response,
            pidx=provider_response.get("pidx", ""),
        )

        return payment, provider_response.get("payment_url", "")

    @staticmethod
    @transaction.atomic
    def initiate(
        payment,
        provider_response,
        *,
        pidx="",
        transaction_id="",
        provider_transaction_id="",
    ):
        if payment.status != Payment.PaymentStatus.PENDING:
            raise ValidationError("Only pending payments can be initiated.")

        return PaymentService._transition(
            payment,
            Payment.PaymentStatus.INITIATED,
            timestamp_field="initiated_at",
            provider_response=provider_response,
            pidx=pidx,
            transaction_id=transaction_id,
            provider_transaction_id=provider_transaction_id,
        )

    @staticmethod
    @transaction.atomic
    def verify_khalti_payment(payment):
        if payment.status != Payment.PaymentStatus.INITIATED:
            return payment

        gateway = KhaltiGateway()

        try:
            lookup_response = gateway.lookup(payment.pidx)
        except KhaltiGatewayError:
            PaymentService.mark_verification_attempt(payment)
            raise

        khalti_status = lookup_response.get("status")

        if khalti_status == "Completed":
            verified_amount = Decimal(
                lookup_response.get("total_amount", 0)
            ) / Decimal(100)

            return PaymentService.complete(
                payment,
                verified_amount=verified_amount,
                provider_transaction_id=lookup_response.get(
                    "transaction_id", ""
                ),
                verification_response=lookup_response,
            )

        if khalti_status in {"Expired", "User canceled", "Refunded"}:
            return PaymentService.fail(
                payment,
                reason=f"Khalti reported status '{khalti_status}'.",
                verification_response=lookup_response,
            )

        PaymentService.mark_verification_attempt(
            payment, verification_response=lookup_response
        )
        return payment

    @staticmethod
    @transaction.atomic
    def complete(payment, verified_amount, provider_transaction_id="", **extra):
        payment = PaymentService._transition(
            payment,
            Payment.PaymentStatus.COMPLETED,
            timestamp_field="completed_at",
            verified_amount=verified_amount,
            provider_transaction_id=provider_transaction_id,
            **extra,
        )

        WalletService.credit_provider_earning(payment)

        return payment

    @staticmethod
    @transaction.atomic
    def fail(payment, reason="", **extra):
        return PaymentService._transition(
            payment,
            Payment.PaymentStatus.FAILED,
            timestamp_field="failed_at",
            failure_reason=reason,
            **extra,
        )

    @staticmethod
    @transaction.atomic
    def cancel(payment, reason=""):
        return PaymentService._transition(
            payment,
            Payment.PaymentStatus.CANCELLED,
            timestamp_field="cancelled_at",
            failure_reason=reason,
        )

    @staticmethod
    def mark_verification_attempt(payment, verification_response=None):
        payment.verification_attempts += 1
        payment.last_verification_attempt_at = timezone.now()

        if verification_response is not None:
            payment.verification_response = verification_response

        if payment.verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
            payment.status = Payment.PaymentStatus.FAILED
            payment.failed_at = timezone.now()
            payment.failure_reason = "Verification retries exhausted."
            payment.next_verification_at = None
        else:
            payment.next_verification_at = (
                timezone.now()
                + PaymentService._backoff_delay(payment.verification_attempts)
            )

        payment.save()
        return payment

    @staticmethod
    def _backoff_delay(attempt_number):
        index = min(attempt_number - 1, len(VERIFICATION_BACKOFF_SECONDS) - 1)
        return timedelta(seconds=VERIFICATION_BACKOFF_SECONDS[index])

    @staticmethod
    def get_payments_due_for_verification():
        """Used by the Celery beat task to find INITIATED Khalti payments
        that are ready for another lookup attempt."""
        now = timezone.now()
        return Payment.objects.filter(
            status=Payment.PaymentStatus.INITIATED,
            provider=Payment.PaymentProvider.KHALTI,
        ).filter(
            models.Q(next_verification_at__lte=now)
            | models.Q(next_verification_at__isnull=True)
        )
