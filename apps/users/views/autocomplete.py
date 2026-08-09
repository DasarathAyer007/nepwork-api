from django.db.models import Q
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from apps.users.models import User


class UserAutocompleteSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "account_type",
            "profile_picture",
        ]

    def get_profile_picture(self, obj: User) -> str | None:
        request = self.context.get("request")
        return obj.get_absolute_avatar_url(request)


class UserAutocompleteView(ListAPIView):
    """
    GET /api/users/autocomplete/?q=...
    Returns basic info for active users matching q by full_name, username, or email.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserAutocompleteSerializer
    pagination_class = None

    def get_queryset(self):
        q = (
            self.request.query_params.get("q")
            or self.request.query_params.get("search")
            or ""
        )
        q = q.strip()
        qs = User.objects.all()

        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(full_name__icontains=q)
                | Q(email__icontains=q)
            )

        return qs.order_by("full_name", "username")[:20]
