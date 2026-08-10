from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Payout, Wallet
from ..serializers.wallet_serializers import (
    CreatePayoutSerializer,
    LedgerEntrySerializer,
    PayoutSerializer,
    WalletSerializer,
)
from ..services.wallet_services import WalletService


@extend_schema(tags=["Wallet"])
class MyWalletView(APIView):
    """Provider-facing: current balance + recent ledger activity."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = WalletService.get_or_create_wallet(request.user)
        entries = wallet.entries.all()[:50]

        return Response(
            {
                "wallet": WalletSerializer(wallet).data,
                "recent_entries": LedgerEntrySerializer(
                    entries, many=True
                ).data,
            }
        )


@extend_schema(tags=["Wallet"])
class MyPayoutsView(APIView):
    """Provider-facing: list of their own payouts."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = WalletService.get_or_create_wallet(request.user)
        payouts = wallet.payouts.all()
        return Response(PayoutSerializer(payouts, many=True).data)


@extend_schema(tags=["Wallet - Admin"])
class AdminCreatePayoutView(APIView):
    """
    Admin-facing: create a PENDING payout for a provider's wallet.
    This is step 1 of the manual payout flow - the admin then actually sends
    the money outside the system (bank transfer / Khalti personal transfer)
    and calls AdminCompletePayoutView to close it out.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = CreatePayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payout = WalletService.create_payout(
                wallet=serializer.wallet,
                amount=serializer.validated_data["amount"],
                method=serializer.validated_data.get("method", "manual"),
                note=serializer.validated_data.get("note", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            PayoutSerializer(payout).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Wallet - Admin"])
class AdminCompletePayoutView(APIView):
    """Admin-facing: confirm a payout has actually been sent, closing the loop."""

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        payout = get_object_or_404(Payout, pk=pk)

        try:
            payout = WalletService.complete_payout(payout)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            PayoutSerializer(payout).data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Wallet - Admin"])
class AdminWalletListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        wallets = Wallet.objects.select_related("user").all()
        return Response(WalletSerializer(wallets, many=True).data)
