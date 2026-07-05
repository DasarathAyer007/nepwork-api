import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

from apps.notifications.services import NotificationService

from .router import WebSocketRouter

logger = logging.getLogger(__name__)


class AppConsumer(AsyncWebsocketConsumer):
    """
    Single WebSocket consumer for the entire application.
    Responsibilities:
      1. Authenticate the connecting user
      2. Join the user's personal group + any chat groups they belong to
      3. Route inbound messages to the correct handler via WebSocketRouter
      4. Forward channel-layer events back to the client (outbound methods)
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

        # Send initial unread notification count on connect
        unread_count = await NotificationService.get_unread_count(self.user)
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection.established",
                    "payload": {
                        "user_id": str(self.user.id),
                        "unread_notifications": unread_count,
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
