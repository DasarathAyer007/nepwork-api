from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/   - paginated notification history for the
    authenticated user, newest first. Supports ?unread=true to filter
    unread only.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("sender")
            .order_by("-created_at")
        )
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        return qs


class NotificationLatestView(generics.ListAPIView):
    """
    GET /api/notifications/latest/  - latest 10 notifications for the
    notification bell dropdown.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            Notification.objects.filter(recipient=self.request.user)
            .select_related("sender")
            .order_by("-created_at")[:10]
        )


class NotificationUnreadCountView(APIView):
    """
    GET /api/notifications/unread-count/  - fast endpoint for badge counts
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    """
    PATCH /api/notifications/<id>/read/    mark a single notification as read
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(
            Notification,
            id=pk,
            recipient=request.user,
        )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """
    POST /api/notifications/read-all/   mark every notification as read
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({"marked_read": updated})


class NotificationDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/notifications/<id>/
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
