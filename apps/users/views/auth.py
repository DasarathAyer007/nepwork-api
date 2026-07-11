# accounts/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import CustomTokenObtainPairSerializer
from ..services.social_auth import (
    get_or_create_social_user,
    verify_facebook_token,
    verify_google_token,
)


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
