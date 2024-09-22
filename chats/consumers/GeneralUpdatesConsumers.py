from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from chats.models import ChatRoom, UserChatRoom, Message, Notification
from chats.signals import activity_notification, message_notification
from api.serializers.chats_serializers import NotificationSerializer
from asgiref.sync import sync_to_async
import logging 

logger = logging.getLogger(__name__)


class GeneralUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        print(self.user)
        if not self.user or self.user.is_anonymous or not self.user.is_authenticated:
            await self.close()  # Close the connection for unauthenticated users
            return  # Exit early
        
        chat_rooms = await self.get_user_chat_rooms()
        for chat_room_id in chat_rooms:
            group_name = f"chat_{chat_room_id}"
            # Add the user's channel to each chat room's group
            await self.channel_layer.group_add(
                group_name,
                self.channel_name
            )
        await self.accept()
        activity_notification.connect(self.send_notification)
        message_notification.connect(self.send_message)

    async def disconnect(self, close_code):
        if not self.user or self.user.is_anonymous or not self.user.is_authenticated:
            return 
        
        # Remove the user from all chat room groups on disconnect
        chat_rooms = await self.get_user_chat_rooms()
        for chat_room_id in chat_rooms:
            group_name = f"chat_{chat_room_id}"
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name
            )
            activity_notification.disconnect(self.send_notification)
            message_notification.disconnect(self.send_message)

    async def receive(self, text_data):
        """Handle incoming messages when the user sends a message."""
        logger.info(f"Received message from {self.user.username}: {text_data}")


    @database_sync_to_async
    def save_notification(self, **kwargs):
        """Save the message to the database."""
        logger.info(f"Received notification {kwargs}")
        kwargs.pop('signal')
        notification_type = kwargs.pop('type')
        user = kwargs.get("user")
        
        if notification_type == "Message":
            kwargs["body"] = f"New messages from {user.username}"
        elif notification_type == "Reaction":
            reaction = kwargs.pop("reaction")
            message_id = reaction.get('message')
            message = Message.objects.filter(id=message_id).first()
            kwargs["body"] = f"{user.username} reacted {reaction.get('reaction_type')} to your message {message.content}"
        elif notification_type == "Join":
            logger.info(f"Received join {kwargs}")
            kwargs["body"] = f"{user} just joined the group"
        elif notification_type == "Leave":
            logger.info(f"Received leave {kwargs}")
            kwargs["body"] = f"{user} just left the group"

        notification = Notification.objects.create(
            **kwargs
        )
        return notification

    @database_sync_to_async
    def save_message(self, chat_room_id, message_data):
        """Save the message to the database."""
        chat_room = ChatRoom.objects.get(id=chat_room_id)
        users_chat_rooms = UserChatRoom.objects.filter(chat_room=chat_room)
        message = Message.objects.create(
            chat_room=chat_room, **message_data
        )
        for user_chat_room in users_chat_rooms:
            user_chat_room.last_sent_message = message
            user_chat_room.save()
        return message

    async def send_notification(self, **kwargs):
        """Send notification updates to the user."""
        sender, type = kwargs.pop('sender'), kwargs.get('type')
        notification = await self.save_notification(**kwargs)
        chat_room_id = kwargs.get('chat_room').id
        room_group_name = f'chat_{chat_room_id}'
        notification_data = await sync_to_async(lambda: NotificationSerializer(notification).data)()
        await self.channel_layer.group_send(
            room_group_name,
            {
                'type': 'notification_update',
                'data': {
                   'type': type,
                       'notification': notification_data
              }
            }
        )

    async def send_message(self, **kwargs):
        """Handle the logic when a user sends a message."""
        logger.info(f"Received message notification: {kwargs}")
        sender, type = kwargs.pop('sender'), kwargs.pop('type')
        message = kwargs.get('message')
        chat_room_id = message.get('chat_room')
        print(chat_room_id)
        room_group_name = f'chat_{chat_room_id}'
        await self.channel_layer.group_send(
            room_group_name,
            {
                'type': 'chat_message',
                'data': {
                    'type': type,
                    'message': message
                }
            }
        )
        logger.info(f"Sent message to group {room_group_name}")

    async def chat_message(self, event):
        """Receive and forward the chat message to the WebSocket."""
        logger.info(f"Sending message to WebSocket: {event}")
        data = event['data']
        await self.send(text_data=json.dumps({
            'type': data['type'],
            'message': data['message'],
        }))
        logger.info("Message sent to WebSocket")

    async def notification_update(self, event):
        """Receive and forward the chat message to the WebSocket."""
        data = event.get('data')
        await self.send(text_data=json.dumps({
            'type': data.get('type'),
            'notification': data.get('notification'),
        }))

    @database_sync_to_async
    def get_user_chat_rooms(self):
        """Fetch chat room IDs the user is associated with."""
        group_chat_rooms = ChatRoom.objects.filter(
            user_chats__user=self.user,
            user_chats__is_active=True,
            room_type='group'
        ).distinct().values_list('id', flat=True)
        
        private_chat_rooms = ChatRoom.objects.filter(
            user_chats__user=self.user,
            room_type='private'
        ).distinct().values_list('id', flat=True)
        
        return list(group_chat_rooms) + list(private_chat_rooms)