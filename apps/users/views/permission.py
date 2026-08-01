from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import Permission, User, UserPermission
from apps.users.permissions import HasPermission
from apps.users.serializers import (
    PermissionSerializer,
    UserPermissionGrantSerializer,
    UserPermissionSerializer,
)
from apps.users.services.permissions import can_manage_user_permissions


class PermissionListView(ListAPIView):
    queryset = Permission.objects.all().order_by("code")
    serializer_class = PermissionSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, HasPermission("permissions.view")]


class UserPermissionListView(ListAPIView):
    serializer_class = UserPermissionSerializer
    pagination_class = None
    permission_classes = [
        IsAuthenticated,
        HasPermission(["users.edit", "permissions.edit"]),
    ]

    def get_queryset(self):
        queryset = UserPermission.objects.select_related("permission").order_by(
            "permission__code"
        )
        user_id = self.request.query_params.get("user_id")
        if user_id:
            target = get_object_or_404(User, id=user_id)
            if not can_manage_user_permissions(self.request.user, target):
                raise PermissionDenied(
                    "You may only view permission overrides for admins strictly below your own role."
                )
            queryset = queryset.filter(user_id=user_id)
        return queryset


class UserPermissionGrantView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasPermission(["users.edit", "permissions.edit"]),
    ]

    def post(self, request, *args, **kwargs):
        serializer = UserPermissionGrantSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        override = serializer.save()
        return Response(UserPermissionSerializer(override).data)


class UserPermissionRevokeView(DestroyAPIView):
    queryset = UserPermission.objects.all()
    lookup_field = "id"
    permission_classes = [
        IsAuthenticated,
        HasPermission(["users.edit", "permissions.edit"]),
    ]

    def delete(self, request, *args, **kwargs):
        override = get_object_or_404(UserPermission, id=kwargs["id"])
        if not can_manage_user_permissions(request.user, override.user):
            raise PermissionDenied(
                "You may only manage permissions for admins strictly below your own role."
            )
        override.delete()
        return Response(status=204)
