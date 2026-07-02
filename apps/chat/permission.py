from rest_framework.permissions import BasePermission

from .models import Chat


class IsChatMember(BasePermission):
    """
    Object-level permission — only members of a chat can access it.
    Works for both detail views (obj = Chat instance) and list/action views
    where chat_id comes from the URL kwargs.
    """

    message = "You are not a member of this chat."

    def has_permission(self, request, view):
        # For views that take chat_id as a URL kwarg (MessageListView, etc.)
        chat_id = view.kwargs.get("chat_id")
        if chat_id:
            return Chat.objects.filter(
                id=chat_id, members=request.user
            ).exists()
        return True  # defer to has_object_permission for detail views

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Chat):
            return obj.members.filter(id=request.user.id).exists()
        return False
