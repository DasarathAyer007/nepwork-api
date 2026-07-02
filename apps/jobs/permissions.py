from apps.users.permissions import IsOwnerAdminOrReadOnly


class IsJobOwnerOrAdminReadOnly(IsOwnerAdminOrReadOnly):
    owner_field = "posted_by"
