import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User

# Rest of your conftest.py code...
@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='12345')

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from chats.models import ChatRoom, UserChatRoom, Message, Attachment, Reaction

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user1():
    return User.objects.create_user(username='user1', email='user1@example.com', password='password123')

@pytest.fixture
def user2():
    return User.objects.create_user(username='user2', email='user2@example.com', password='password123')

@pytest.fixture
def admin_user():
    return User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass123')

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@pytest.fixture
def authenticated_client(api_client, user1):
    tokens = get_tokens_for_user(user1)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
    return api_client

@pytest.fixture
def chatroom(user1, user2):
    room = ChatRoom.objects.create(name='Test Room', room_type='group')
    UserChatRoom.objects.create(user=user1, chat_room=room)
    UserChatRoom.objects.create(user=user2, chat_room=room)
    return room

@pytest.fixture
def private_chatroom(user1, user2):
    room = ChatRoom.objects.create(room_type='private')
    UserChatRoom.objects.create(user=user1, chat_room=room)
    UserChatRoom.objects.create(user=user2, chat_room=room)
    return room

@pytest.fixture
def message(chatroom, user1):
    return Message.objects.create(chat_room=chatroom, sender=user1, content='Test message')

@pytest.fixture
def attachment(message, user1):
    message.user = user1
    return Attachment.objects.create(message=message, file_type='image', file='test.jpg')

@pytest.fixture
def reaction(message, user1):
    return Reaction.objects.create(message=message, user=user1, reaction_type='like')