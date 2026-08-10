import logging

from celery import shared_task

from apps.payment.models import Payment
from apps.payment.services.khalti_service import KhaltiGatewayError
from apps.payment.services.payment_service import PaymentService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def verify_pending_khalti_payments(self):
    payments = PaymentService.get_payments_due_for_verification()

    results = {
        "checked": 0,
        "completed": 0,
        "failed": 0,
        "still_pending": 0,
        "errors": 0,
    }

    for payment in payments:
        results["checked"] += 1
        try:
            updated = PaymentService.verify_khalti_payment(payment)
        except KhaltiGatewayError as exc:
            logger.warning(
                "Khalti lookup failed for payment %s: %s", payment.id, exc
            )
            results["errors"] += 1
            continue

        if updated.status == Payment.PaymentStatus.COMPLETED:
            results["completed"] += 1
        elif updated.status == Payment.PaymentStatus.FAILED:
            results["failed"] += 1
        else:
            results["still_pending"] += 1

    logger.info("Khalti reconciliation run: %s", results)
    return results


@shared_task
def verify_single_khalti_payment(payment_id):
    from apps.payment.models import Payment

    payment = Payment.objects.get(id=payment_id)

    if payment.status != Payment.PaymentStatus.INITIATED:
        return f"Payment {payment_id} already in status '{payment.status}', skipping."

    try:
        PaymentService.verify_khalti_payment(payment)
    except KhaltiGatewayError as exc:
        logger.warning(
            "Khalti lookup failed for payment %s: %s", payment_id, exc
        )

    return f"Verification attempted for payment {payment_id}."
