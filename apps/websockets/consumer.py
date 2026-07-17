import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.chat.services import ChatService
from apps.notifications.services import NotificationService
from apps.websockets.presence import PresenceService

from .router import WebSocketRouter

logger = logging.getLogger(__name__)


class AppConsumer(AsyncWebsocketConsumer):
    """
    Single WebSocket consumer for the entire application.
    Responsibilities:
      1. Authenticate the connecting user
      2. Join the user's personal group + any chat groups they belong to
      3. Track online presence using PresenceService and notify contacts
      4. Route inbound messages to the correct handler via WebSocketRouter
      5. Forward channel-layer events back to the client (outbound methods)
    """

    router = WebSocketRouter()

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Personal group — the ONLY group this consumer joins. All chat
        # messages, typing indicators, and notifications are delivered here.
        # This means a brand-new chat (created mid-session, after connect())
        # works identically to an old one — there's no per-chat group to go
        # stale, no membership bookkeeping needed when a chat is created.
        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        await self.accept()

        # Mark user online and notify contacts
        await PresenceService.set_online(self.user.id)
        contact_ids = await ChatService.get_all_contacts_ids(self.user)
        for contact_id in contact_ids:
            await self.channel_layer.group_send(
                f"user_{contact_id}",
                {
                    "type": "user_presence",
                    "payload": {
                        "user_id": str(self.user.id),
                        "online": True,
                    },
                },
            )

        # Send initial unread counts on connect — lets the frontend hydrate
        # chatSlice/notificationsSlice from this one event instead of a
        # separate HTTP call for each.
        unread_notifications = await NotificationService.get_unread_count(
            self.user
        )
        unread_chat_messages = await ChatService.get_unread_count(self.user)
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection.established",
                    "payload": {
                        "user_id": str(self.user.id),
                        "unread_notifications": unread_notifications,
                        "unread_chat_messages": unread_chat_messages,
                    },
                }
            )
        )

        logger.info(
            "WebSocket connected: user=%s channel=%s",
            self.user.id,
            self.channel_name,
        )

    async def disconnect(self, close_code):
        if hasattr(self, "user") and self.user.is_authenticated:
            # Mark user offline and notify contacts
            await PresenceService.set_offline(self.user.id)
            contact_ids = await ChatService.get_all_contacts_ids(self.user)
            for contact_id in contact_ids:
                await self.channel_layer.group_send(
                    f"user_{contact_id}",
                    {
                        "type": "user_presence",
                        "payload": {
                            "user_id": str(self.user.id),
                            "online": False,
                        },
                    },
                )

        # Leave personal group
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(
                self.user_group, self.channel_name
            )

        logger.info(
            "WebSocket disconnected: user=%s code=%s",
            getattr(self.user, "id", "?"),
            close_code,
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json_error("Invalid JSON payload")
            return

        await self.router.dispatch(data, consumer=self)

    # ------------------------------------------------------------------ #
    #  Outbound event methods (called BY the channel layer)               #
    #  Method name = event["type"] with dots replaced by underscores      #
    # ------------------------------------------------------------------ #

    async def chat_message(self, event):
        """Broadcast a new chat message to all members of a chat group."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat.message",
                    "payload": event["payload"],
                }
            )
        )

    async def chat_created(self, event):
        """Broadcast a newly created chat."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat.created",
                    "payload": event["payload"],
                }
            )
        )

    async def chat_read_confirmed(self, event):
        """Broadcast read receipt confirmation to members."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat.read_confirmed",
                    "payload": event["payload"],
                }
            )
        )

    async def typing_indicator(self, event):
        """Broadcast typing status to all members of a chat group."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat.typing",
                    "payload": event["payload"],
                }
            )
        )

    async def notification_new(self, event):
        """Push a new notification to a specific user's personal group."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification.new",
                    "payload": event["payload"],
                }
            )
        )

    async def notification_read_confirmed(self, event):
        """Confirm notification read status to the recipient's connections."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification.read_confirmed",
                    "payload": event["payload"],
                }
            )
        )

    async def notification_read_all_confirmed(self, event):
        """Confirm all notifications read status to the recipient's connections."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification.read_all_confirmed",
                    "payload": event["payload"],
                }
            )
        )

    async def user_presence(self, event):
        """Broadcast presence updates to contacts."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user.presence",
                    "payload": event["payload"],
                }
            )
        )

    # ------------------------------------------------------------------ #
    #  Utility                                                             #
    # ------------------------------------------------------------------ #

    async def send_json_error(self, message: str, code: str = "error"):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "payload": {"code": code, "message": message},
                }
            )
        )
