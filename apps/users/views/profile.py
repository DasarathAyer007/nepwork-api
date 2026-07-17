from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.models.user import User
from apps.users.serializers.ProfileReadSerializer import (
    ProfileReadSerializer,
)
from apps.users.serializers.ProfileWriteSerializer import (
    OrganizationProfileWriteSerializer,
    PersonalProfileWriteSerializer,
)


class UpdateProfileView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        print("REQUEST DATA:")
        print(request.data)
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        user = self.request.user

        if user.account_type == User.AccountType.PERSONAL:
            return user.personal_profile

        return user.organization_profile

    def get_serializer_class(self):
        user = self.request.user

        if user.account_type == User.AccountType.PERSONAL:
            return PersonalProfileWriteSerializer

        return OrganizationProfileWriteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return FULL profile data instead of write serializer data
        read_serializer = ProfileReadSerializer(
            request.user,
            context={"request": request},
        )

        return Response(
            read_serializer.data,
            status=status.HTTP_200_OK,
        )
