from asgiref.sync import async_to_sync
from bleach import clean
from channels.layers import get_channel_layer
from django.db.models import Count

from apps.chat.models import Chat, Message
from apps.chat.serializers import MessageSerializer
from apps.utils.emails.email_service import EmailService


def _get_or_create_direct_chat(user_a, user_b):
    chat = (
        Chat.objects.filter(members=user_a)
        .filter(members=user_b)
        .annotate(member_count=Count("members"))
        .filter(member_count=2)
        .first()
    )
    if chat is None:
        chat = Chat.objects.create()
        chat.members.add(user_a, user_b)
    return chat


def _send_chat_message(sender, recipient, content: str):
    chat = _get_or_create_direct_chat(sender, recipient)
    message = Message.objects.create(chat=chat, sender=sender, content=content)

    channel_layer = get_channel_layer()
    payload = MessageSerializer(message).data
    for member_id in {sender.id, recipient.id}:
        async_to_sync(channel_layer.group_send)(
            f"user_{member_id}",
            {"type": "chat_message", "payload": payload},
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
        EmailService.send_application_status_email(
            applicant=applicant,
            job_title=application.job.title,
            status_label=status_label,
            message=plain_text,
        )
