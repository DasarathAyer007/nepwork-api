from django.db.models import Count, Q
from rest_framework import serializers
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.user_activity.models import UserActivity
from apps.users.permissions import HasPermission
from apps.utils.pagination import CustomPageNumberPagination


class UserMinimalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    account_type = serializers.CharField()
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, instance):
        request = self.context.get("request")
        return (
            instance.get_absolute_avatar_url(request)
            if hasattr(instance, "get_absolute_avatar_url")
            else None
        )


class UserActivitySerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = UserActivity
        fields = [
            "id",
            "user",
            "activity_type",
            "object_type",
            "object_id",
            "metadata",
            "created_at",
        ]


class UserActivityListView(ListAPIView):
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated, HasPermission("users.view")]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        qs = UserActivity.objects.select_related("user").order_by("-created_at")
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(object_id__icontains=search)
            )

        user_id = self.request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)

        activity_type = self.request.query_params.get("activity_type")
        if activity_type:
            qs = qs.filter(activity_type=activity_type)

        object_type = self.request.query_params.get("object_type")
        if object_type:
            qs = qs.filter(object_type=object_type)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        ordering = self.request.query_params.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)

        return qs


class UserActivityStatsView(GenericAPIView):
    permission_classes = [IsAuthenticated, HasPermission("users.view")]

    def get(self, request):
        total = UserActivity.objects.count()
        by_activity_type = dict(
            UserActivity.objects.values("activity_type")
            .annotate(count=Count("id"))
            .values_list("activity_type", "count")
        )
        by_object_type = dict(
            UserActivity.objects.values("object_type")
            .annotate(count=Count("id"))
            .values_list("object_type", "count")
        )

        return Response(
            {
                "total": total,
                "by_activity_type": by_activity_type,
                "by_object_type": by_object_type,
            }
        )
