from django.db import IntegrityError
import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from chats.models import ChatRoom, UserChatRoom, Message, Attachment, Reaction, Notification
from django.utils import timezone
from datetime import timedelta

@pytest.fixture
def users():
    return [
        User.objects.create_user(username=f'user{i}', password='password') 
        for i in range(1, 6)
    ]

@pytest.mark.django_db
class TestChatRoom:
    def test_create_private_chat(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        assert chat.room_type == 'private'
        assert chat.user_chats.count() == 2

    def test_create_duplicate_private_chat(self, users):
        chat1 = ChatRoom.get_or_create_private_chat(users[0], users[1])
        chat2 = ChatRoom.get_or_create_private_chat(users[0], users[1])
        assert chat1 == chat2

    def test_create_group_chat(self, users):
        chat = ChatRoom.objects.create(room_type='group')
        for user in users[:3]:
            UserChatRoom.objects.create(user=user, chat_room=chat)
        assert chat.user_chats.count() == 3

    def test_chat_room_str_representation(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        assert str(chat) == f'private created for user1,user2'

@pytest.mark.django_db
class TestUserChatRoom:
    def test_soft_delete(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        user_chat = UserChatRoom.objects.get(user=users[0], chat_room=chat)
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        user_chat.soft_delete()
        assert not user_chat.is_active
        assert Message.objects.get(id=message.id).sender is None

    def test_name_property_private_chat(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        user_chat = UserChatRoom.objects.get(user=users[0], chat_room=chat)
        assert user_chat.name == 'user2'

    def test_name_property_group_chat(self, users):
        chat = ChatRoom.objects.create(room_type='group')
        for user in users[:3]:
            UserChatRoom.objects.create(user=user, chat_room=chat)
        user_chat = UserChatRoom.objects.get(user=users[0], chat_room=chat)
        assert user_chat.name == 'group with user2,user3'

    def test_new_messages_property(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        user_chat = UserChatRoom.objects.get(user=users[0], chat_room=chat)
        Message.objects.create(chat_room=chat, sender=users[1], content=b"Test message 1")
        Message.objects.create(chat_room=chat, sender=users[1], content=b"Test message 2")
        assert user_chat.new_messages.count() == 2

@pytest.mark.django_db
class TestMessage:
    def test_soft_delete(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        message.soft_delete()
        assert message.is_deleted
        assert message.content == b'This message was deleted.'

    def test_message_ordering(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message1 = Message.objects.create(chat_room=chat, sender=users[0], content=b"First message")
        message2 = Message.objects.create(chat_room=chat, sender=users[1], content=b"Second message")
        assert list(chat.messages.all()) == [message1, message2]

@pytest.mark.django_db
class TestAttachment:
    def test_valid_attachment(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        image_file = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        attachment = Attachment.objects.create(message=message, file_type='image', file=image_file)
        assert attachment.file_type == 'image'

    def test_invalid_attachment_type(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        invalid_file = SimpleUploadedFile("test_file.txt", b"file_content", content_type="text/plain")
        with pytest.raises(ValidationError):
            Attachment.objects.create(message=message, file_type='image', file=invalid_file)

    def test_attachment_soft_delete(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        image_file = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        attachment = Attachment.objects.create(message=message, file_type='image', file=image_file)
        attachment.soft_delete()
        assert attachment.message is None

@pytest.mark.django_db
class TestReaction:
    def test_create_reaction(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        reaction = Reaction.objects.create(message=message, user=users[1], reaction_type='like')
        assert reaction.reaction_type == 'like'

    def test_unique_reaction_per_user_per_message(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        Reaction.objects.create(message=message, user=users[1], reaction_type='like')
        with pytest.raises(IntegrityError):
            Reaction.objects.create(message=message, user=users[1], reaction_type='love')

    def test_multiple_reactions_different_users(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Test message")
        Reaction.objects.create(message=message, user=users[1], reaction_type='like')
        Reaction.objects.create(message=message, user=users[2], reaction_type='love')
        assert message.reactions.count() == 2

@pytest.mark.django_db
class TestNotification:
    def test_create_notification(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        notification = Notification.objects.create(
            body="New message in chat",
            user=users[0],
            chat_room=chat
        )
        assert notification.user == users[0]
        assert notification.chat_room == chat

    def test_notification_ordering(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        notification1 = Notification.objects.create(
            body="First notification",
            user=users[0],
            chat_room=chat
        )
        notification2 = Notification.objects.create(
            body="Second notification",
            user=users[0],
            chat_room=chat
        )
        assert list(Notification.objects.all()) == [notification2, notification1]

# Additional complex scenarios

@pytest.mark.django_db
class TestComplexScenarios:
    def test_multi_user_chat_with_reactions_and_attachments(self, users):
        # Create a group chat
        chat = ChatRoom.objects.create(room_type='group')
        for user in users:
            UserChatRoom.objects.create(user=user, chat_room=chat)

        # Send messages with attachments
        message1 = Message.objects.create(chat_room=chat, sender=users[0], content=b"First message")
        image_file = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        Attachment.objects.create(message=message1, file_type='image', file=image_file)

        message2 = Message.objects.create(chat_room=chat, sender=users[1], content=b"Second message")
        doc_file = SimpleUploadedFile("test_doc.pdf", b"file_content", content_type="application/pdf")
        Attachment.objects.create(message=message2, file_type='document', file=doc_file)

        # Add reactions
        Reaction.objects.create(message=message1, user=users[2], reaction_type='like')
        Reaction.objects.create(message=message1, user=users[3], reaction_type='love')
        Reaction.objects.create(message=message2, user=users[4], reaction_type='laugh')

        # Assertions
        assert chat.messages.count() == 2
        assert message1.attachment.file_type == 'image'
        assert message2.attachment.file_type == 'document'
        assert message1.reactions.count() == 2
        assert message2.reactions.count() == 1

    def test_user_leaving_and_rejoining_chat(self, users):
        # Create a group chat
        chat = ChatRoom.objects.create(room_type='group')
        for user in users[:3]:
            UserChatRoom.objects.create(user=user, chat_room=chat)

        # User leaves the chat
        user_chat = UserChatRoom.objects.get(user=users[0], chat_room=chat)
        user_chat.soft_delete()

        # Send a message after user has left
        Message.objects.create(chat_room=chat, sender=users[1], content=b"Message while user0 is away")

        # User rejoins the chat
        UserChatRoom.objects.create(user=users[0], chat_room=chat)

        # Assert that the user can see the message sent while they were away
        new_user_chat = UserChatRoom.objects.get(user=users[0], chat_room=chat, is_active=True)
        assert new_user_chat.new_messages.count() == 1

    def test_message_editing_and_deletion_history(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])
        
        # Create and edit a message
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"Original content")
        message.content = b"Edited content"
        message.is_edited = True
        message.save()

        # Soft delete the message
        message.soft_delete()

        # Assertions
        assert message.is_edited
        assert message.is_deleted
        assert message.content == b'This message was deleted.'

    def test_chat_room_with_multiple_attachment_types(self, users):
        chat = ChatRoom.objects.create(room_type='group')
        for user in users:
            UserChatRoom.objects.create(user=user, chat_room=chat)

        # Create messages with different attachment types
        message_types = [
            ('image', 'test_image.jpg', 'image/jpeg'),
            ('document', 'test_doc.pdf', 'application/pdf'),
            ('audio', 'test_audio.mp3', 'audio/mpeg'),
            ('video', 'test_video.mp4', 'video/mp4')
        ]

        for i, (file_type, filename, content_type) in enumerate(message_types):
            binary_content = "Message with {}".format(file_type).encode('utf-8')
            message = Message.objects.create(chat_room=chat, sender=users[i], content=binary_content)
            file = SimpleUploadedFile(filename, b"file_content", content_type=content_type)
            Attachment.objects.create(message=message, file_type=file_type, file=file)

        # Assertions
        assert chat.messages.count() == 4
        for message in chat.messages.all():
            assert message.attachment.file_type in [t[0] for t in message_types]

    def test_notification_creation_for_various_events(self, users):
        chat = ChatRoom.get_or_create_private_chat(users[0], users[1])

        # New message notification
        message = Message.objects.create(chat_room=chat, sender=users[0], content=b"New message")
        Notification.objects.create(
            body=f"New message from {users[0].username}",
            user=users[1],
            chat_room=chat
        )

        # Reaction notification
        reaction = Reaction.objects.create(message=message, user=users[1], reaction_type='like')
        Notification.objects.create(
            body=f"{users[1].username} reacted to your message",
            user=users[0],
            chat_room=chat
        )

        # User joined notification
        new_user = User.objects.create_user(username='newuser', password='password')
        UserChatRoom.objects.create(user=new_user, chat_room=chat)
        for user in [users[0], users[1]]:
            Notification.objects.create(
                body=f"{new_user.username} joined the chat",
                user=user,
                chat_room=chat
            )

        # Assertions
        assert Notification.objects.filter(chat_room=chat).count() == 4
        assert Notification.objects.filter(user=users[0]).count() == 2
        assert Notification.objects.filter(user=users[1]).count() == 2