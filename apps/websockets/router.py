import logging

from .handlers import ChatHandler, NotificationHandler

logger = logging.getLogger(__name__)

# Maps every inbound msg type to the handler class responsible for it.
# Adding a new feature = add entries here + create a handler file.
# AppConsumer never needs to change.
HANDLER_MAP: dict = {
    # Chat
    "chat.send": ChatHandler,
    "chat.typing": ChatHandler,
    "chat.read": ChatHandler,
    # Notifications
    "notification.read": NotificationHandler,
    "notification.read_all": NotificationHandler,
}


class WebSocketRouter:
    async def dispatch(self, data: dict, consumer):
        msg_type = data.get("type")

        if not msg_type:
            await consumer.send_json_error("Missing 'type' field in message")
            return

        HandlerClass = HANDLER_MAP.get(msg_type)

        if not HandlerClass:
            logger.warning("No handler registered for msg type: %s", msg_type)
            await consumer.send_json_error(
                f"Unknown message type: '{msg_type}'"
            )
            return

        try:
            handler = HandlerClass(consumer)
            await handler.handle(data)
        except Exception as exc:
            logger.exception(
                "Unhandled error in handler %s: %s", HandlerClass.__name__, exc
            )
            await consumer.send_json_error("Internal server error")
