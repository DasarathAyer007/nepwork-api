from rest_framework import serializers

from ..models import LedgerEntry, Payout, Wallet


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "entry_type",
            "reason",
            "amount",
            "balance_after",
            "payment",
            "created_at",
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "balance", "updated_at"]
        read_only_fields = fields


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id",
            "amount",
            "status",
            "method",
            "note",
            "processed_at",
            "created_at",
        ]
        read_only_fields = ["id", "status", "processed_at", "created_at"]


class CreatePayoutSerializer(serializers.Serializer):
    """Used by the admin-facing 'trigger a payout' endpoint."""

    wallet_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01
    )
    method = serializers.CharField(max_length=20, default="manual")
    note = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )

    def validate_wallet_id(self, value):
        try:
            self.wallet = Wallet.objects.get(pk=value)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Wallet not found.")
        return value
