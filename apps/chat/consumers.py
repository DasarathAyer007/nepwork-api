# # chat/consumers.py
# import json

# from channels.db import database_sync_to_async
# from channels.generic.websocket import AsyncWebsocketConsumer

# from .models import Chat, Message
# from .serializers import MessageSerializer


# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         print("🔥 ASGI CONNECT WORKING")

#         self.user = self.scope["user"]


#         if not self.user or not self.user.is_authenticated:
#             await self.close()
#             return

#         # One personal group per user — covers ALL chats
#         self.user_group = f"user_{self.user.id}"
#         await self.channel_layer.group_add(self.user_group, self.channel_name)
#         await self.accept()

#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.user_group, self.channel_name
#         )

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         msg_type = data.get("type")

#         if msg_type == "message":
#             chat_id = data.get("chat_id")
#             content = data.get("content", "").strip()
#             if not content or not chat_id:
#                 return

#             is_member = await self.check_membership(chat_id)
#             if not is_member:
#                 return

#             message = await self.save_message(chat_id, content)
#             serialized = await self.serialize_message(message)
#             member_ids = await self.get_member_ids(chat_id)

#             # Push to every member of this chat via their personal group
#             for uid in member_ids:
#                 await self.channel_layer.group_send(
#                     f"user_{uid}",
#                     {
#                         "type": "chat_message",
#                         "chat_id": str(chat_id),
#                         "message": serialized,
#                     },
#                 )

#         elif msg_type == "typing":
#             chat_id = data.get("chat_id")
#             is_typing = data.get("is_typing", False)
#             member_ids = await self.get_member_ids(chat_id)

#             for uid in member_ids:
#                 if uid != self.user.id:
#                     await self.channel_layer.group_send(
#                         f"user_{uid}",
#                         {
#                             "type": "typing_indicator",
#                             "chat_id": str(chat_id),
#                             "username": self.user.username,
#                             "is_typing": is_typing,
#                         },
#                     )

#     async def chat_message(self, event):
#         await self.send(
#             text_data=json.dumps(
#                 {
#                     "type": "message",
#                     "chat_id": event["chat_id"],
#                     "message": event["message"],
#                 }
#             )
#         )

#     async def typing_indicator(self, event):
#         await self.send(
#             text_data=json.dumps(
#                 {
#                     "type": "typing",
#                     "chat_id": event["chat_id"],
#                     "username": event["username"],
#                     "is_typing": event["is_typing"],
#                 }
#             )
#         )

#     # --- DB helpers ---

#     @database_sync_to_async
#     def check_membership(self, chat_id):
#         return Chat.objects.filter(id=chat_id, members=self.user).exists()

#     @database_sync_to_async
#     def save_message(self, chat_id, content):
#         chat = Chat.objects.get(id=chat_id)
#         return Message.objects.create(
#             chat=chat, sender=self.user, content=content
#         )

#     @database_sync_to_async
#     def serialize_message(self, message):
#         return MessageSerializer(message).data

#     @database_sync_to_async
#     def get_member_ids(self, chat_id):
#         chat = Chat.objects.get(id=chat_id)
#         return list(chat.members.values_list("id", flat=True))

#         # @database_sync_to_async

#     # def save_message(self, chat_id, text):
#     #     chat = Chat.objects.get(id=chat_id)

#     #     msg = Message.objects.create(
#     #         chat=chat,
#     #         sender=self.user,
#     #         text=text
#     #     )

#     #     return {
#     #         "id": str(msg.id),
#     #         "text": msg.text,
#     #         "sender": msg.sender_id
#     #     }
