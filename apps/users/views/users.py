import json

from django.db import transaction
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
    UpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.locations.serializers import (
    LocationSerializer,
    LocationWriteSerializer,
)
from apps.users.models.user import User
from apps.users.permissions import HasPermission
from apps.users.serializers.ProfileWriteSerializer import (
    OrganizationProfileWriteSerializer,
    PersonalProfileWriteSerializer,
)
from apps.users.services.permissions import get_effective_permission_codes
from apps.utils.users_utils import get_auth_user

from ..schemas import ONBOARDING_SCHEMA, USER_LOCATION_SCHEMA
from ..serializers import (
    AdminCreateSerializer,
    CustomTokenObtainPairSerializer,
    ProfileReadSerializer,
    UserRegisterSerializer,
)
from ..services.otp_services import OTPService
from ..services.user_services import UserService

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
                "message": "Registration successful. Please verify your email.",
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyOTPView(GenericAPIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response(
                {"message": "email and otp are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if OTPService.verify_signup_otp(user, otp):
            token_data = CustomTokenObtainPairSerializer.build_response_data(
                user,
                request,
            )
            return Response(
                {
                    "message": "OTP verified successfully.",
                    **token_data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"message": "Invalid or expired OTP."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ResendOTPView(GenericAPIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")

        if not email:
            return Response(
                {"message": "email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_active:
            return Response(
                {"message": "Account is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OTPService.send_signup_otp(user)

        return Response(
            {
                "message": "OTP resent successfully.",
                "cooldown_seconds": 60,
            },
            status=status.HTTP_200_OK,
        )


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class MeView(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        admin_profile = getattr(user, "admin_profile", None)
        role_data = None
        if admin_profile and admin_profile.role_id:
            role_data = {
                "code": admin_profile.role.code,
                "name": admin_profile.role.name,
            }

        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "account_type": user.account_type,
                    "profile_picture": user.get_absolute_avatar_url(request),
                    "is_onboarded": user.is_onboarded(),
                    "is_superuser": user.is_superuser,
                },
                "role": role_data,
                "permissions": sorted(get_effective_permission_codes(user)),
            }
        )


class AdminCreateView(CreateAPIView):
    serializer_class = AdminCreateSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.edit")]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Admin account created successfully.",
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


@ONBOARDING_SCHEMA
class OnboardingView(CreateAPIView):
    permission_classes = [IsAuthenticated]

    def _resolve_account_type(self, request):
        requested = (
            request.data.get("account_type") or request.user.account_type
        )

        account_type_map = {
            "personal": User.AccountType.PERSONAL,
            "organization": User.AccountType.ORGANIZATION,
            User.AccountType.PERSONAL: User.AccountType.PERSONAL,
            User.AccountType.ORGANIZATION: User.AccountType.ORGANIZATION,
        }

        account_type = account_type_map.get(requested)

        if account_type is None:
            raise ValidationError(
                {
                    "account_type": "Onboarding is only available for personal or organization accounts."
                }
            )

        return account_type

    def get_serializer_class(self):
        user = get_auth_user(self.request)

        if not user:
            raise PermissionDenied(
                "Authentication credentials were not provided."
            )

        account_type = self._resolve_account_type(self.request)

        if account_type == User.AccountType.PERSONAL:
            return PersonalProfileWriteSerializer

        return OrganizationProfileWriteSerializer

    def _save_location(self, user, request):
        raw_location = request.data.get("location")

        if not raw_location:
            return

        try:
            location_data = (
                json.loads(raw_location)
                if isinstance(raw_location, str)
                else raw_location
            )
        except json.JSONDecodeError:
            return

        if (
            not location_data
            or location_data.get("lat") is None
            or location_data.get("lng") is None
        ):
            return

        location_serializer = LocationWriteSerializer(data=location_data)
        location_serializer.is_valid(raise_exception=True)
        location = location_serializer.save()

        user.location = location
        user.save(update_fields=["location"])

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        account_type = self._resolve_account_type(request)

        user = get_auth_user(self.request)

        if user and account_type != user.account_type:
            user.account_type = account_type
            user.save(update_fields=["account_type"])

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(user=request.user)

        self._save_location(request.user, request)

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
    ).select_related("admin_profile", "admin_profile__role")
    serializer_class = ProfileReadSerializer

    def get_object(self):
        queryset = self.get_queryset()
        # decide filter based on which kwarg is present in the URL
        if "username" in self.kwargs:
            obj = get_object_or_404(queryset, username=self.kwargs["username"])
        elif "id" in self.kwargs:
            obj = get_object_or_404(queryset, id=self.kwargs["id"])
        else:
            raise NotFound("No lookup field provided.")

        self.check_object_permissions(self.request, obj)
        return obj


class ProfileUpdateView(UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = get_auth_user(self.request)

        if user and user.account_type == User.AccountType.PERSONAL:
            return user.personal_profile

        if user and user.account_type == User.AccountType.ORGANIZATION:
            return user.organization_profile

        raise NotFound("Profile not found.")

    def get_serializer_class(self):
        user = get_auth_user(self.request)

        if user and user.account_type == User.AccountType.PERSONAL:
            return PersonalProfileWriteSerializer

        if user and user.account_type == User.AccountType.ORGANIZATION:
            return OrganizationProfileWriteSerializer

        raise ValidationError("Invalid account type.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            ProfileReadSerializer(
                request.user,
                context={"request": request},
            ).data
        )


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
