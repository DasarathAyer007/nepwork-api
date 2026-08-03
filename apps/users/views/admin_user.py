from rest_framework import serializers
from rest_framework.generics import ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.models import AdminProfile, User
from apps.users.permissions import CanManageAdminUser, HasPermission
from apps.users.serializers import AdminUpdateSerializer


class AdminUserListSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "status",
            "role",
            "date_joined",
        ]

    def get_role(self, instance: User) -> dict[str, str] | None:
        admin_profile = getattr(instance, "admin_profile", None)
        if not admin_profile or not admin_profile.role_id:
            return None
        return {
            "code": admin_profile.role.code,
            "name": admin_profile.role.name,
        }


class AdminUserListView(ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    queryset = (
        User.objects.filter(account_type=User.AccountType.ADMIN)
        .select_related("admin_profile", "admin_profile__role")
        .order_by("-date_joined")
    )


class AdminUserUpdateView(UpdateAPIView):
    """Updates an existing admin's role/status/department/designation.
    Object-level access is limited to superadmins or strictly-senior admins
    (see `CanManageAdminUser`) — a peer or junior admin gets a 403."""

    serializer_class = AdminUpdateSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "id"
    permission_classes = [
        IsAuthenticated,
        HasPermission("users.edit"),
        CanManageAdminUser,
    ]
    queryset = AdminProfile.objects.select_related("user", "role")

    def update(self, request, *args, **kwargs):
        admin_profile = self.get_object()
        serializer = self.get_serializer(
            admin_profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserListSerializer(admin_profile.user).data)


class CandidateUserListView(ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    queryset = User.objects.filter(
        account_type=User.AccountType.PERSONAL
    ).order_by("-date_joined")
