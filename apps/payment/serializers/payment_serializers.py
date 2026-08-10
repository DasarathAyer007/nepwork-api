from decimal import Decimal
from urllib.parse import urlparse

from rest_framework import serializers

from apps.services.models import ServiceRequest
from config.payment_gateway import FRONTEND_URL

from ..models import Payment


class InitiateKhaltiPaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )
    return_url = serializers.URLField(required=False, allow_blank=True)

    def validate_return_url(self, value):
        if not value:
            return value

        allowed_origin = urlparse(str(FRONTEND_URL)).netloc
        origin = urlparse(value).netloc

        if origin != allowed_origin:
            raise serializers.ValidationError(
                "return_url must point back to the NepWork app."
            )

        return value

    def validate_order_id(self, value):
        try:
            order = ServiceRequest.objects.select_related(
                "user", "service"
            ).get(pk=value)
        except ServiceRequest.DoesNotExist:
            raise serializers.ValidationError("Service request not found.")

        request = self.context["request"]

        if order.user_id != request.user.id:
            raise serializers.ValidationError(
                "You do not have permission to pay for this service request."
            )

        if order.status != ServiceRequest.ServiceRequestStatus.ACCEPTED:
            raise serializers.ValidationError(
                "Only accepted service requests can be paid for."
            )

        self.order = order
        return value

    def validate(self, attrs):
        order = self.order
        attrs["amount"] = attrs.get("amount") or order.budget

        if not attrs["amount"]:
            raise serializers.ValidationError(
                {"amount": "An amount is required to initiate payment."}
            )

        return attrs


class KhaltiInitiateResponseSerializer(serializers.ModelSerializer):
    payment_url = serializers.CharField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "reference",
            "provider",
            "status",
            "amount",
            "currency",
            "pidx",
            "payment_url",
        ]
        read_only_fields = fields


class VerifyKhaltiPaymentSerializer(serializers.Serializer):
    pidx = serializers.CharField()


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "provider",
            "amount",
            "currency",
            "verified_amount",
            "refunded_amount",
            "status",
            "reference",
            "provider_transaction_id",
            "pidx",
            "failure_reason",
            "verification_attempts",
            "initiated_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
        ]
        read_only_fields = fields
