from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payment.models import Payment

from ..serializers.payment_serializers import (
    InitiateKhaltiPaymentSerializer,
    KhaltiInitiateResponseSerializer,
    PaymentSerializer,
    VerifyKhaltiPaymentSerializer,
)
from ..services.khalti_service import KhaltiGatewayError
from ..services.payment_service import PaymentService


@extend_schema(tags=["Payments"])
class InitiateKhaltiPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateKhaltiPaymentSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        order = serializer.order
        user = request.user
        user_info = {
            "name": user.full_name or user.username,
            "email": user.email,
            "phone": user.phone_number,
        }

        try:
            payment, payment_url = PaymentService.initiate_khalti_payment(
                order=order,
                amount=serializer.validated_data["amount"],
                user_info=user_info,
                return_url=serializer.validated_data.get("return_url"),
            )
        except KhaltiGatewayError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.payment_url = payment_url
        response_serializer = KhaltiInitiateResponseSerializer(payment)

        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Payments"])
class VerifyKhaltiPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, order__user=request.user)

        try:
            payment = PaymentService.verify_khalti_payment(payment)
        except KhaltiGatewayError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            PaymentSerializer(payment).data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Payments"])
class VerifyKhaltiPaymentByPidxView(APIView):
    """
    Lets the UI run the Khalti lookup itself right after the user is
    redirected back from Khalti, using the `pidx` Khalti appends to the
    return_url — without needing to know the internal Payment id.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyKhaltiPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = get_object_or_404(
            Payment,
            pidx=serializer.validated_data["pidx"],
            order__user=request.user,
        )

        try:
            payment = PaymentService.verify_khalti_payment(payment)
        except KhaltiGatewayError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY
            )
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            PaymentSerializer(payment).data, status=status.HTTP_200_OK
        )


@extend_schema(tags=["Payments"])
class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk, order__user=request.user)
        return Response(PaymentSerializer(payment).data)
