from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import (
    CreateAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.models.user import User
from apps.users.serializers.ProfileWriteSerializer import (
    OrganizationProfileWriteSerializer,
    PersonalProfileWriteSerializer,
)
from apps.utils.users_utils import get_auth_user

from .schemas import ONBOARDING_SCHEMA
from .serializers import (
    CustomTokenObtainPairSerializer,
    ProfileReadSerializer,
    UserRegisterSerializer,
)
from .services import UserService

# User = get_user_model()


class RegisterView(CreateAPIView[User]):
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = UserService.register_user(
            full_name=data["full_name"],
            email=data["email"],
            username=data["username"],
            password=data["password"],
            account_type=data["account_type"],
        )

        return Response(
            {
                "message": "Registration successful. Please check your email.",
                "user_id": user.id,
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@ONBOARDING_SCHEMA
class OnboardingView(CreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        user = get_auth_user(self.request)

        if not user:
            raise PermissionDenied(
                "Authentication credentials were not provided."
            )
        account_type = user.account_type
        if account_type == User.AccountType.PERSONAL:
            return PersonalProfileWriteSerializer

        if account_type == User.AccountType.ORGANIZATION:
            return OrganizationProfileWriteSerializer

        raise ValidationError(
            {
                "account_type": "Onboarding is only available for personal or organization accounts."
            }
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user)

        return Response(
            {
                "message": "Profile created successfully.",
                "data": ProfileReadSerializer(
                    request.user,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileDetailView(RetrieveAPIView):
    queryset = User.objects.prefetch_related(
        "personal_profile",
        "organization_profile",
    )
    serializer_class = ProfileReadSerializer
    lookup_field = "id"
