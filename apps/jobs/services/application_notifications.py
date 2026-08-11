from asgiref.sync import async_to_sync
from bleach import clean
from channels.layers import get_channel_layer

from apps.chat.models import Message
from apps.chat.serializers import ChatSerializer, MessageSerializer
from apps.chat.services import ChatService
from apps.jobs.tasks import (
    send_applicant_decision_email,
    send_application_status_email,
)


def _send_chat_message(sender, recipient, content: str):
    chat, created = ChatService.get_or_create_direct_chat_sync(
        {sender.id, recipient.id}
    )
    message = Message.objects.create(chat=chat, sender=sender, content=content)

    channel_layer = get_channel_layer()
    message_payload = MessageSerializer(message).data
    chat_payload = ChatSerializer(chat).data if created else None
    for member_id in {sender.id, recipient.id}:
        if created:
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
        send_application_status_email.delay(
            application_id=str(application.id),
            status_label=status_label,
            message=plain_text,
        )


def notify_applicant_decision(
    application,
    applicant,
    decision_label: str,
    message: str,
    send_message: bool = True,
    send_email: bool = True,
):
    """Deliver an applicant's accept/decline decision to the employer via chat and/or email."""
    plain_text = clean(message, tags=[], strip=True).strip()
    if not plain_text:
        return

    employer = application.job.posted_by

    if send_message:
        _send_chat_message(
            sender=applicant, recipient=employer, content=plain_text
        )

    if send_email and employer.email:
        send_applicant_decision_email.delay(
            application_id=str(application.id),
            decision_label=decision_label,
            message=plain_text,
        )
