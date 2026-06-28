from rest_framework import status
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    RetrieveAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.locations.serializer import (
    LocationSerializer,
    LocationWriteSerializer,
)
from apps.users.models.user import User
from apps.users.serializers.ProfileWriteSerializer import (
    OrganizationProfileWriteSerializer,
    PersonalProfileWriteSerializer,
)
from apps.utils.users_utils import get_auth_user

from .schemas import ONBOARDING_SCHEMA, USER_LOCATION_SCHEMA
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

    def get_object(self):
        queryset = self.get_queryset()
        # decide filter based on which kwarg is present in the URL
        if "username" in self.kwargs:
            obj = get_object_or_404(queryset, username=self.kwargs["username"])
            print(f"Retrieved user by username: {obj.username}")
        elif "id" in self.kwargs:
            obj = get_object_or_404(queryset, id=self.kwargs["id"])
            print(f"Retrieved user by ID: {obj.id}")
        else:
            raise NotFound("No lookup field provided.")

        self.check_object_permissions(self.request, obj)
        return obj


@USER_LOCATION_SCHEMA
class UserLocationView(GenericAPIView):
    # permission_classes = [IsAuthenticated]
    def get_object(self, user_id):
        user = get_object_or_404(User, id=user_id)
        return user.location

    def get(self, request, user_id):
        location = self.get_object(user_id)
        if not location:
            return Response(
                {"detail": "Location not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LocationSerializer(location, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = LocationWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        location = serializer.save()

        user.location = location
        user.save(update_fields=["location"])

        return Response(
            LocationSerializer(location, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, user_id, *args, **kwargs):
        location = self.get_object(user_id)
        if not location:
            return Response(
                {"message": "Location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = LocationWriteSerializer(location, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "message": "Location updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
