from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from users.models import Profile
User = get_user_model()

class UserStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        
        if self.scope["user"].is_anonymous or not self.scope["user"].is_authenticated:
            await self.close()
            return
        
        await self.accept()
        await self.update_user_status(True)
        await self.channel_layer.group_add("online_users", self.channel_name)

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.update_user_status(False)
            await self.channel_layer.group_discard("online_users", self.channel_name)
        
    async def receive(self, text_data):
        pass  # Add any custom logic for receiving messages

    @database_sync_to_async
    def update_user_status(self, is_online):
        status = 'online' if is_online else 'offline'
        user = self.user
        profile = Profile.objects.filter(user=user).first()
        profile.status = status
        profile.save()
