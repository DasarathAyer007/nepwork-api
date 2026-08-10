from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import LedgerEntry, Payout, Wallet


class WalletService:
    @staticmethod
    def get_or_create_wallet(user):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        return wallet

    @staticmethod
    @transaction.atomic
    def _record_entry(wallet, entry_type, reason, amount, payment=None):
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if entry_type == LedgerEntry.EntryType.DEBIT:
            new_balance = wallet.balance - amount
            if new_balance < 0:
                raise ValueError("Insufficient wallet balance for this debit.")
        else:
            new_balance = wallet.balance + amount

        entry = LedgerEntry.objects.create(
            wallet=wallet,
            payment=payment,
            entry_type=entry_type,
            reason=reason,
            amount=amount,
            balance_after=new_balance,
        )

        wallet.balance = new_balance
        wallet.save(update_fields=["balance", "updated_at"])

        return entry

    @staticmethod
    def get_commission_rate():
        # TODO :: Need to Make this dynamic in the future, maybe from a DB table or settings. For now, it's hardcoded to 10%.
        return Decimal(
            str(getattr(settings, "PLATFORM_COMMISSION_RATE", "0.10"))
        )

    @staticmethod
    @transaction.atomic
    def credit_provider_earning(payment):
        provider_user = payment.order.service.user
        wallet = WalletService.get_or_create_wallet(provider_user)

        commission_rate = WalletService.get_commission_rate()
        commission = (payment.amount * commission_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        provider_earning = payment.amount - commission

        return WalletService._record_entry(
            wallet,
            entry_type=LedgerEntry.EntryType.CREDIT,
            reason=LedgerEntry.Reason.SERVICE_EARNING,
            amount=provider_earning,
            payment=payment,
        )

    @staticmethod
    @transaction.atomic
    def create_payout(wallet, amount, method="manual", note=""):
        if amount <= 0:
            raise ValueError("Payout amount must be positive.")

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if amount > wallet.balance:
            raise ValueError("Payout amount exceeds wallet balance.")

        return Payout.objects.create(
            wallet=wallet, amount=amount, method=method, note=note
        )

    @staticmethod
    @transaction.atomic
    def complete_payout(payout):
        if payout.status != Payout.Status.PENDING:
            raise ValueError(
                f"Cannot complete a payout in status '{payout.status}'."
            )

        WalletService._record_entry(
            payout.wallet,
            entry_type=LedgerEntry.EntryType.DEBIT,
            reason=LedgerEntry.Reason.PAYOUT,
            amount=payout.amount,
        )

        payout.status = Payout.Status.COMPLETED
        payout.processed_at = timezone.now()
        payout.save(update_fields=["status", "processed_at", "updated_at"])

        return payout

    @staticmethod
    @transaction.atomic
    def fail_payout(payout, note=""):
        if payout.status != Payout.Status.PENDING:
            raise ValueError(
                f"Cannot fail a payout in status '{payout.status}'."
            )

        payout.status = Payout.Status.FAILED
        if note:
            payout.note = note
        payout.save(update_fields=["status", "note", "updated_at"])

        return payout
