import json
import logging

logger = logging.getLogger(__name__)


class BaseHandler:
    """
    All handlers inherit from this.
    Gives every handler access to the consumer, user, and channel layer,
    plus shared helpers for sending messages back to clients.
    """

    def __init__(self, consumer):
        self.consumer = consumer
        self.user = consumer.user
        self.channel_layer = consumer.channel_layer

    async def handle(self, data: dict):
        raise NotImplementedError("Each handler must implement handle()")

    # ------------------------------------------------------------------ #
    #  Outbound helpers                                                    #
    # ------------------------------------------------------------------ #

    async def reply(self, msg_type: str, payload: dict):
        """Send a message back to THIS specific socket only."""
        await self.consumer.send(
            text_data=json.dumps(
                {
                    "type": msg_type,
                    "payload": payload,
                }
            )
        )

    async def send_error(self, message: str, code: str = "error"):
        """Send an error frame back to THIS specific socket."""
        await self.consumer.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "payload": {"code": code, "message": message},
                }
            )
        )

    async def send_to_group(
        self, group_name: str, event_type: str, payload: dict
    ):
        """
        Broadcast to all sockets in a channel-layer group.
        event_type must map to a method on AppConsumer (dots → underscores).
        e.g. "chat_message" calls consumer.chat_message(event)
        """
        await self.channel_layer.group_send(
            group_name,
            {
                "type": event_type,
                "payload": payload,
            },
        )

    async def send_to_user(self, user_id: int, event_type: str, payload: dict):
        """Push directly to a specific user's personal group."""
        await self.send_to_group(f"user_{user_id}", event_type, payload)
