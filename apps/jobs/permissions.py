from apps.users.permissions import IsOwnerAdminOrReadOnly


class IsJobOwnerOrAdmin(IsOwnerAdminOrReadOnly):
    owner_field = "posted_by"
