# accounts/views.py
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from ..models.user import User
from ..serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    ForgotPasswordRequestSerializer,
    ForgotPasswordResetSerializer,
    ForgotPasswordVerifyOTPSerializer,
)
from ..services.otp_services import OTPService
from ..services.social_auth import (
    get_or_create_social_user,
    verify_facebook_token,
    verify_google_token,
)


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordRequestView(GenericAPIView):
    permission_classes = []
    serializer_class = ForgotPasswordRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.get(email__iexact=email)
        OTPService.send_forgot_password_otp(user)

        return Response(
            {"message": f"A verification code has been sent to {email}."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordVerifyOTPView(GenericAPIView):
    permission_classes = []
    serializer_class = ForgotPasswordVerifyOTPSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not OTPService.verify_forgot_password_otp(user, otp):
            return Response(
                {"message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "OTP verified successfully."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordResetView(GenericAPIView):
    permission_classes = []
    serializer_class = ForgotPasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not OTPService.reset_password_with_otp(user, otp, new_password):
            return Response(
                {"message": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Password reset successfully. You can now log in."},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "refresh is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_205_RESET_CONTENT)


class GoogleLoginView(APIView):
    permission_classes = []

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response(
                {"detail": "token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            info = verify_google_token(token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED
            )

        user, created = get_or_create_social_user(info, provider="google")

        if not user.is_active:
            return Response(
                {"detail": "This account has been deactivated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = CustomTokenObtainPairSerializer.build_response_data(
            user, request
        )
        data["created"] = created
        return Response(
            data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class FacebookLoginView(APIView):
    permission_classes = []

    def post(self, request):
        access_token = request.data.get("access_token")
        if not access_token:
            return Response(
                {"detail": "access_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            info = verify_facebook_token(access_token)
        except ValueError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED
            )

        user, created = get_or_create_social_user(info, provider="facebook")

        if not user.is_active:
            return Response(
                {"detail": "This account has been deactivated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = CustomTokenObtainPairSerializer.build_response_data(
            user, request
        )
        data["created"] = created
        return Response(
            data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
