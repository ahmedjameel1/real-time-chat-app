from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User
from chats.models import ChatRoom, UserChatRoom, Message, Attachment, Reaction, Notification
from model_bakery import baker




class APITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password123')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password123')
        self.admin_user = User.objects.create_superuser(username='admin', email='admin@example.com', password='adminpass123')

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_user_registration(self):
        url = reverse('users-list')
        data = {
            'first_name': 'John',
            'last_name': 'Adam',
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test registration with existing email
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test registration with invalid email
        data['email'] = 'invalid_email'
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_obtain(self):
        url = reverse('token_obtain_pair')
        data = {
            'email': 'user1@example.com',
            'password': 'password123'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        # Test with incorrect password
        data['password'] = 'wrongpassword'
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_refresh(self):
        obtain_url = reverse('token_obtain_pair')
        refresh_url = reverse('token_refresh')
        data = {
            'email': 'user1@example.com',
            'password': 'password123'
        }
        response = self.client.post(obtain_url, data)
        refresh_token = response.data['refresh']

        response = self.client.post(refresh_url, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

        # Test with invalid refresh token
        response = self.client.post(refresh_url, {'refresh': 'invalid_token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_users_list(self):
        self.authenticate(self.user1)
        url = reverse('users-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_user_retrieve(self):
        self.authenticate(self.user1)
        url = reverse('users-detail', kwargs={'pk': self.user2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user2.email)

        # Test retrieving non-existent user
        url = reverse('users-detail', kwargs={'pk': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_update(self):
        self.authenticate(self.user1)
        url = reverse('users-detail', kwargs={'pk': self.user1.pk})
        data = {'username': 'updateduser1'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'updateduser1')

        # Test updating another user's profile
        url = reverse('users-detail', kwargs={'pk': self.user2.pk})
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_delete(self):
        self.authenticate(self.user1)
        url = reverse('users-detail', kwargs={'pk': self.user1.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Test deleting another user's account
        self.authenticate(self.user2)
        url = reverse('users-detail', kwargs={'pk': self.admin_user.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_chat_rooms(self):
        self.authenticate(self.user1)
        chat_room = baker.make(ChatRoom, room_type='group')
        url = reverse('user-chats-list')

        # Create user chat room
        data = {'chat_room': chat_room.id, 'user': self.user1.id, 'name': 'user1'}
        response = self.client.post(url, data)
        print('-##########################',response, '----------<')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Retrieve user chat rooms
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

        # Retrieve specific user chat room
        user_chat_room_id = response.data[0]['id']
        url = reverse('user-chats-detail', kwargs={'pk': user_chat_room_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_messages(self):
        import base64
        self.authenticate(self.user1)
        chat_room = ChatRoom.objects.create(room_type='group')
        UserChatRoom.objects.create(user=self.user1, chat_room=chat_room)
        url = reverse('messages-list')

        # Test case 1: Base64 encoded string
        data = {'chat_room': chat_room.id, 'content': "aGVsbG8="}
        response = self.client.post(url, data)
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Update message
        message_id = response.data['id']
        update_url = reverse('messages-detail', kwargs={'pk': message_id})
        updated_base64_content = "aGVsbG8="
        data = {'content': updated_base64_content}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Delete message
        response = self.client.delete(update_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


    def test_reactions(self):
        self.authenticate(self.user1)
        chat_room = ChatRoom.objects.create(room_type='group')
        message = Message.objects.create(chat_room=chat_room, sender=self.user1, content=b'Test message')
        url = reverse('reactions-list')

        # Create reaction
        data = {'message': message.id, 'reaction_type': 'like'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reaction_id = response.data['id']

        # List reactions
        response = self.client.get(url, {'message': message.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

        # Update reaction
        url = reverse('reactions-detail', kwargs={'pk': reaction_id})
        data = {'reaction_type': 'love'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reaction_type'], 'love')

        # Delete reaction
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)