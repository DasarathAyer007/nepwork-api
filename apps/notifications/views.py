from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import HasPermission

from .models import Notification
from .serializers import (
    AdminNotificationCreateSerializer,
    AdminNotificationUpdateSerializer,
    NotificationSerializer,
)


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
            .select_related("sender", "recipient")
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
            .select_related("sender", "recipient")
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
        return Response(
            NotificationSerializer(
                notification, context={"request": request}
            ).data
        )


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


# ==========================================
# Admin Notification Endpoints (RBAC Managed)
# ==========================================


class AdminNotificationListView(generics.ListCreateAPIView):
    """
    GET  /api/notifications/admin/ - List all system notifications with filtering
    POST /api/notifications/admin/ - Admin send/create notification
    """

    permission_classes = [IsAuthenticated, HasPermission("communication.view")]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminNotificationCreateSerializer
        return NotificationSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("communication.edit")()]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        qs = Notification.objects.select_related(
            "sender", "recipient"
        ).order_by("-created_at")

        notification_type = self.request.query_params.get("notification_type")
        is_read = self.request.query_params.get("is_read")
        sender_id = self.request.query_params.get("sender_id")
        recipient_id = self.request.query_params.get("recipient_id")
        search = self.request.query_params.get(
            "search"
        ) or self.request.query_params.get("q")

        if notification_type:
            qs = qs.filter(notification_type=notification_type)

        if is_read is not None and is_read != "":
            if is_read.lower() == "true":
                qs = qs.filter(is_read=True)
            elif is_read.lower() == "false":
                qs = qs.filter(is_read=False)

        if sender_id:
            qs = qs.filter(sender_id=sender_id)

        if recipient_id:
            qs = qs.filter(recipient_id=recipient_id)

        if search:
            search = search.strip()
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(message__icontains=search)
                | Q(sender__username__icontains=search)
                | Q(sender__full_name__icontains=search)
                | Q(sender__email__icontains=search)
                | Q(recipient__username__icontains=search)
                | Q(recipient__full_name__icontains=search)
                | Q(recipient__email__icontains=search)
            )

        return qs

    def perform_create(self, serializer):
        serializer.save()


class AdminNotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/notifications/admin/<id>/ - Retrieve notification detail
    PATCH  /api/notifications/admin/<id>/ - Update notification
    DELETE /api/notifications/admin/<id>/ - Delete notification
    """

    queryset = Notification.objects.select_related("sender", "recipient")

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminNotificationUpdateSerializer
        return NotificationSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH"]:
            return [IsAuthenticated(), HasPermission("communication.edit")()]
        if self.request.method == "DELETE":
            return [IsAuthenticated(), HasPermission("communication.delete")()]
        return [IsAuthenticated(), HasPermission("communication.view")()]
