"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# from channels.auth import AuthMiddlewareStack
# from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

from apps.chat.middleware import JWTAuthMiddleware
from apps.websockets.consumer import AppConsumer

# import apps.chat.routing


print("ASGI application is starting...")
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": JWTAuthMiddleware(
            URLRouter(
                [
                    path("ws/app/", AppConsumer.as_asgi()),
                ]
            )
        ),
    }
)


# application = ProtocolTypeRouter({
#     "websocket": AllowedHostsOriginValidator(
#         AuthMiddlewareStack(
#             URLRouter([
#                 path("ws/app/", AppConsumer.as_asgi()),
#             ])
#         )
#     ),
# })

# application = get_asgi_application()

# django_asgi_app = get_asgi_application()

# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             apps.chat.routing.websocket_urlpatterns
#         )
#     ),
# })
