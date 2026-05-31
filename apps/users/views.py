from uuid import UUID

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import (
    CreateAPIView,
    GenericAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.models.user import User
from apps.users.serializers.ProfileWriteSerializer import (
    OrganizationProfileWriteSerializer,
    PersonalProfileWriteSerializer,
)
from apps.utils.users_utils import get_auth_user

from .permissions import IsOwnerAdminOrReadOnly
from .serializers import (
    AdminProfileReadSerializer,
    BaseProfileResponseSerializer,
    CustomTokenObtainPairSerializer,
    OrganizationProfileReadSerializer,
    PersonalProfileReadSerializer,
    UserRegisterSerializer,
)
from .services import ProfileService

# User = get_user_model()


class RegisterView(CreateAPIView[User]):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# class ProfileCreate(GenericAPIView):
#     permission_classes = [IsOwnerAdminOrReadOnly]

#     def get_write_serializer(self , user:User| None):
#         if user and user.account_type == User.AccountType.ORGANIZATION:
#             return OrganizationProfileWriteSerializer
#         return PersonalProfileWriteSerializer
#     def post(self, request: Request) ->Response:
#             user = get_auth_user(self.request)
#             serializer_class =self.get_write_serializer(user)
#             serializer = serializer_class(data=request.data)
#             if serializer.is_valid():
#                 serializer.save()
#                 return Response(serializer.data)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileCreate(GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        user = get_auth_user(self.request)

        # if not user:
        #     raise PermissionDenied("Authentication credentials were not provided.")

        if user and user.account_type == User.AccountType.ORGANIZATION:
            return OrganizationProfileWriteSerializer

        return PersonalProfileWriteSerializer

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=get_auth_user(request))
        return Response(serializer.data)


class ProfileGet(APIView):
    permission_classes = [IsOwnerAdminOrReadOnly]

    def get(self, request: Request, user_id: UUID) -> Response:
        tagret_user = get_object_or_404(User, id=user_id)

        user = get_auth_user(request)

        if user is None or not user.is_authenticated:
            raise PermissionDenied(
                "Authentication credentials were not provided."
            )

        serializer_class = self.get_serializer_class(user, tagret_user)

        # profile = getattr(tagret_user, 'profile', None)
        profile = ProfileService.get_profile(user)

        if profile is None:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = serializer_class(profile)
        return Response(serializer.data)

    def get_serializer_class(
        self, current_user: User | None, target_user: User
    ) -> type[BaseProfileResponseSerializer]:
        # is_owner:bool =current_user is not None and  current_user.id == target_user.id

        if target_user.account_type == User.AccountType.ORGANIZATION:
            return (
                OrganizationProfileReadSerializer
                # if is_owner
                # else OrganizationProfilePublicSerializer
            )
        if target_user.account_type == User.AccountType.ADMIN:
            return AdminProfileReadSerializer
        return PersonalProfileReadSerializer
