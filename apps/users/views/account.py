from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..serializers import ConfirmOTPSerializer, RequestEmailChangeSerializer
from ..services.otp_services import OTPService


class RequestEmailChangeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestEmailChangeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["new_email"]

        OTPService.send_change_email_otp(request.user, new_email)

        return Response(
            {
                "message": f"A verification code has been sent to {new_email}.",
            },
            status=status.HTTP_200_OK,
        )


class ConfirmEmailChangeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConfirmOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_email = OTPService.verify_change_email_otp(
            request.user, serializer.validated_data["otp"]
        )

        if not new_email:
            return Response(
                {"message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": "Email address updated successfully.",
                "email": new_email,
            },
            status=status.HTTP_200_OK,
        )


class RequestAccountDeletionView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        OTPService.send_delete_account_otp(request.user)

        return Response(
            {
                "message": f"A verification code has been sent to {request.user.email}.",
            },
            status=status.HTTP_200_OK,
        )


class ConfirmAccountDeletionView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConfirmOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        if not OTPService.verify_delete_account_otp(
            user, serializer.validated_data["otp"]
        ):
            return Response(
                {"message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.delete()

        return Response(
            {"message": "Your account has been permanently deleted."},
            status=status.HTTP_200_OK,
        )
