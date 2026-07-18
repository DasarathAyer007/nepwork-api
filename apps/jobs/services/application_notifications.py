from asgiref.sync import async_to_sync
from bleach import clean
from channels.layers import get_channel_layer

from apps.chat.models import Message
from apps.chat.serializers import ChatSerializer, MessageSerializer
from apps.chat.services import ChatService
from apps.jobs.tasks import send_application_status_email


def _send_chat_message(sender, recipient, content: str):
    # Reuse ChatService's implementation — the ONLY correct "one direct
    # chat per pair" lookup (backed by the direct_pair_key DB constraint).
    # A hand-rolled version used to live here, filtering Chat by two
    # separate .filter(members=...) calls: each creates its own join to
    # the M2M through-table, so the subsequent Count("members") counted
    # across the join cartesian product instead of the real member count,
    # never matching member_count == 2 — so it created a brand new chat
    # on every single call instead of reusing the existing one.
    chat, created = ChatService.get_or_create_direct_chat_sync(
        {sender.id, recipient.id}
    )
    message = Message.objects.create(chat=chat, sender=sender, content=content)

    channel_layer = get_channel_layer()
    message_payload = MessageSerializer(message).data
    chat_payload = ChatSerializer(chat).data if created else None
    for member_id in {sender.id, recipient.id}:
        if created:
            # New chat — every member's sidebar needs the chat object
            # itself, same as the WebSocket chat.start path, or it won't
            # show up until the next full refetch.
            async_to_sync(channel_layer.group_send)(
                f"user_{member_id}",
                {"type": "chat_created", "payload": chat_payload},
            )
        async_to_sync(channel_layer.group_send)(
            f"user_{member_id}",
            {"type": "chat_message", "payload": message_payload},
        )
    return message


def notify_application_status_change(
    application,
    employer,
    status_label: str,
    message: str,
    send_message: bool = True,
    send_email: bool = True,
):
    """Deliver an employer's status-change message via chat and/or email."""
    plain_text = clean(message, tags=[], strip=True).strip()
    if not plain_text:
        return

    applicant = application.applicant

    if send_message:
        _send_chat_message(
            sender=employer, recipient=applicant, content=plain_text
        )

    if send_email and applicant.email:
        # Fire-and-forget via Celery — sending inline here would block on
        # SMTP for the duration of the request, and since this runs under
        # the same thread-sensitive executor as every WebSocket DB call,
        # a slow SMTP send stalls chat message delivery for ALL users
        # until it completes.
        send_application_status_email.delay(
            application_id=str(application.id),
            status_label=status_label,
            message=plain_text,
        )
