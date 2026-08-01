from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.models import Role
from apps.users.permissions import HasPermission, IsSuperAdmin
from apps.users.serializers import (
    RolePermissionUpdateSerializer,
    RoleSerializer,
)


class RoleListView(ListAPIView):
    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, HasPermission("roles.view")]


class RoleDetailView(RetrieveAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    lookup_field = "id"
    permission_classes = [IsAuthenticated, HasPermission("roles.view")]


class RoleUpdatePermissionsView(UpdateAPIView):
    queryset = Role.objects.all()
    serializer_class = RolePermissionUpdateSerializer
    lookup_field = "id"
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def update(self, request, *args, **kwargs):
        role = get_object_or_404(Role, id=kwargs["id"])
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "role": role},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(RoleSerializer(role).data)
