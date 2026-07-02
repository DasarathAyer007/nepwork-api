from apps.users.permissions import IsOwnerAdminOrReadOnly


class IsServiceOwnerOrAdmin(IsOwnerAdminOrReadOnly):
    owner_field = "user"
