import base64
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from users.models import E2EEKey



class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('private', 'Private'),
        ('group', 'Group'),
    )
    e2ee_key = models.OneToOneField(E2EEKey, on_delete=models.CASCADE, null=True, blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        user_chats = self.user_chats.all()
        name = ','.join([u.user.username for u in user_chats])
        return f'{self.room_type} created for {name}'

    @classmethod
    def get_or_create_private_chat(cls, user1, user2):
        # Ensure user1 and user2 are distinct
        if user1 == user2:
            raise ValueError("Users must be different")

        # Find existing private chat between these users
        chat = cls.objects.filter(
            room_type='private',
            user_chats__user=user1
        ).filter(
            user_chats__user=user2
        ).distinct().first()

        if chat:
            return chat

        # Create new private chat if it doesn't exist
        chat = cls.objects.create(room_type='private')
        UserChatRoom.objects.create(user=user1, chat_room=chat)
        UserChatRoom.objects.create(user=user2, chat_room=chat)
        return chat


from django.db import models, IntegrityError

class UserChatRoomManager(models.Manager):
    def create(self, **kwargs):
        user = kwargs.get('user')
        chat_room = kwargs.get('chat_room')

        # Check for existing UserChatRoom instance
        user_chat_room = UserChatRoom.objects.filter(user=user, chat_room=chat_room).first()
        # print(user, chat_room)
        if user_chat_room and user_chat_room.is_active == False:
            user_chat_room.is_active = True
            user_chat_room.save()
            return user_chat_room
        
        # Proceed with the creation
        return super().create(**kwargs)

                    
                
class UserChatRoom(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='user_chats')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # For soft delete
    last_sent_message = models.ForeignKey('Message', on_delete=models.SET_NULL, null=True, blank=True,
    related_name='last_sent_message')
    last_seen_message = models.ForeignKey('Message', null=True, blank=True, on_delete=models.SET_NULL,
    related_name='last_seen_message')
    last_seen_message_before_delete = models.ForeignKey('Message', null=True, blank=True, on_delete=models.SET_NULL,
    related_name='last_seen_message_before_delete')
    is_read = models.BooleanField(default=False)
    
    objects = UserChatRoomManager()

    class Meta:
        unique_together = ('user', 'chat_room')

    def soft_delete(self):
        messages = Message.objects.filter(chat_room=self.chat_room, sender=self.user)
        self.last_seen_message_before_delete = messages.last()
        for message in messages:
            message.sender = None
        Message.objects.bulk_update(messages, ['sender'])
        self.is_active = False
        self.save()

    @property
    def name(self):
        user_chats_in_same_chat_room = self.chat_room.user_chats.filter(is_active=True)
        user_names = [c.user.username for c in user_chats_in_same_chat_room if c.user != self.user]
        if self.chat_room.room_type == 'group':
            return 'group with '+ ",".join(user_names)
        return ",".join(user_names)
    

    def get_full_user_name(self):
        return self.user.first_name.capitalize() + ' ' + self.user.last_name.capitalize()
    

    @property   
    def new_messages(self):
        try:
            chat_room = self.chat_room
            user_chat_state = self
            last_seen_message_before_delete = user_chat_state.last_seen_message_before_delete
        except self.DoesNotExist:
            last_seen_message_before_delete = None

        if last_seen_message_before_delete:
            new_messages = Message.objects.filter(
                chat_room=chat_room,
                sender__isnull=False,
                id__gt=last_seen_message_before_delete.id
            )
        else:
            new_messages = Message.objects.filter(
                chat_room=chat_room,
                sender__isnull=False
            )

        return new_messages


class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.BinaryField()
    public_key = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_deleted = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['timestamp']
    
    def soft_delete(self):
        self.content = b'This message was deleted.'
        reactions = self.reactions.all()
        for r in reactions:
            r.delete()
        self.is_deleted = True
        self.save()

    def save(self, *args, **kwargs):
        if isinstance(self.content, str):
            # Decode the base64 string to binary data
            self.content = base64.b64decode(self.content)
        super().save(*args, **kwargs)
        

class Attachment(models.Model):
    FILE_TYPES = (
        ('image', 'Image'),
        ('document', 'Document'),
        ('audio', 'Audio'),
        ('video', 'Video'),
    )
    
    message = models.OneToOneField(Message, on_delete=models.CASCADE, null=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES, db_index=True)
    file = models.FileField(upload_to='attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        allowed_types = {
            'image': ['jpeg', 'jpg', 'png', 'gif'],
            'document': ['pdf', 'doc', 'docx', 'txt'],
            'audio': ['mp3', 'wav', 'ogg'],
            'video': ['mp4', 'avi', 'mov']
        }
        file_extension = self.file.name.split('.')[-1].lower()
        
        if file_extension not in allowed_types[self.file_type]:
            raise ValidationError(f'Invalid file type: {file_extension}. Allowed types for {self.file_type}: {", ".join(allowed_types[self.file_type])}')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.get_file_type_display()} - {self.file.name}'
    
    def soft_delete(self):
        self.message = None
        self.save()

class Reaction(models.Model):
    REACTION_TYPES = (
        ('like', '👍'),
        ('love', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('angry', '😠'),
    )
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')  # One reaction per user per message
    
    def __str__(self):
        return f'{self.user.username} reacted {self.get_reaction_type_display()} to message in {self.message.chat_room.name}'
    


class Notification(models.Model):
    body = models.TextField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    chat_room = models.ForeignKey('ChatRoom', on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

