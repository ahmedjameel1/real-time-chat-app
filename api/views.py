from rest_framework.viewsets import GenericViewSet, mixins
from rest_framework.viewsets import ModelViewSet
from users.models import User, E2EEKey
from .serializers.users_serializers import UserSerializer, E2EEKeySerializer
from .serializers.customjwttoken import EmailTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from chats.signals import activity_notification, message_notification
import base64
import io
from django.core.files.base import ContentFile
"========================================Users start======================================================"
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser



class E2EEKeyViewSet(ModelViewSet, mixins.CreateModelMixin):
    queryset = E2EEKey.objects.all()
    serializer_class = E2EEKeySerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)  # Use HTTP_201_CREATED for creation

    def list(self, request, *args, **kwargs):
        return Response({'Not allowed': 'These keys are private to the user and are not stored on the server'}, status=status.HTTP_403_FORBIDDEN)

    def retrieve(self, request, *args, **kwargs):
        return Response({'Not allowed': 'These keys are private to the user and are not stored on the server'}, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        return Response({'Not allowed': 'These keys are private to the user and are not stored on the server'}, status=status.HTTP_403_FORBIDDEN)   



class UserViewSet(ModelViewSet):
    """
    User CRUDS
    """
    queryset = User.objects.all()  # Define the queryset here
    serializer_class = UserSerializer
    lookup_field = 'pk'
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # This goes in the view, not the serializer

    def get_permissions(self):
        """
        Return the permission classes for the current request.
        """
        if self.request.method == 'POST':  # If it's a 'create' request
            permission_classes = [AllowAny]  # Allow anyone to create
        else:
            permission_classes = [IsAuthenticated]  # All other requests require authentication
        
        return [permission() for permission in permission_classes]

    def update(self, request, *args, **kwargs):
        """
        Overrides the default update behavior to ensure that a user can only update their own account.
        
        If the instance being updated does not match the authenticated user, a 403 Forbidden response is returned with an error message.
        Otherwise, the default update behavior is called.
        """
        instance = self.get_object()
        if instance != request.user:
            return Response({'error': 'A user can only update his own account.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance != request.user:
            return Response({'error': 'A user can only delete his own account.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)



class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
   
"=======================================Users end========================================================="
"=======================================Chats start======================================================="
from django.db import IntegrityError
from chats.models import (
    ChatRoom,
    UserChatRoom,
    Message,
    Attachment,
    Reaction,
    Notification
)
from .serializers.chats_serializers import (
    ChatRoomSerializer,
    UserChatRoomSerializer,
    MessageSerializer,
    AttachmentSerializer,
    ReactionSerializer,
    NotificationSerializer
)
from rest_framework.decorators import action
# from chats.signals.chats_signals import user_chatroom_activity

class ChatRoomViewSet(ModelViewSet):
    """
    Provides a view for managing chat rooms. This view allows authenticated users to perform CRUD operations on chat rooms they are part of.
    
    The `update` method returns a 403 Forbidden response if the user is not part of the chat room they are trying to update.
    
    The `destroy` method checks if the user is part of the chat room they are trying to delete. If the user is not part of the chat room, a 403 Forbidden response is returned. Otherwise, the chat room is soft deleted.
    
    The `join` action allows authenticated users to join a group chat room. The `leave` action allows authenticated users to leave a group chat room.
    """
    queryset = ChatRoom.objects.all()
    model = ChatRoom
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        users = User.objects.filter(userchatroom__chat_room=instance, userchatroom__is_active=True)
        if request.user not in users:
            return Response({'error': 'User must be part of the chatroom to be able to update it.'})
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    

    @action(detail=True, methods=['post'], url_path='join')
    def join(self, request, *args, **kwargs):
        user = request.user
        chat_room = self.get_object()

        if chat_room.room_type != 'group':
            return Response(
                {'detail': 'Joining chats is restricted to groups only.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Try to get or create the UserChatRoom instance
            user_chat_room, created = UserChatRoom.objects.get_or_create(
                user=user, **request.data
            )
        except IntegrityError:
            # Handle any database integrity issues
            return Response(
                {'detail': 'Unable to join chat room due to a database error.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if created:
            # Trigger the custom signal for joining the chat
            # user_chatroom_activity.send(sender=self.model, user=user, chat_room=chat_room, action='joined')
            activity_notification.send(sender=self.__class__, type='Join', chat_room=chat_room, user=user)
            serializer = UserChatRoomSerializer(user_chat_room)
            return Response(serializer.data, status=status.HTTP_200_CREATED)  # 201 for created
        
        elif not user_chat_room.is_active:
            user_chat_room.is_active = True
            user_chat_room.save()

            # Trigger the custom signal for rejoining the chat
            # user_chatroom_activity.send(sender=self.model, user=user, chat_room=chat_room, action='rejoined')
            
            serializer = UserChatRoomSerializer(user_chat_room)
            activity_notification.send(sender=self.__class__, type='Join', chat_room=chat_room, user=user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {'detail': 'User is already part of the group and active.'},
            status=status.HTTP_200_OK
        )



    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, *args, **kwargs):
        user = request.user
        chat_room = self.get_object()
        
        if chat_room.room_type == 'group':
            # Ensure the user is part of the group and retrieve UserChatRoom instance
            try:
                user_chat_room = UserChatRoom.objects.get(user=user, chat_room=chat_room)
            except UserChatRoom.DoesNotExist:
                return Response({'error': 'User is not part of this group.'}, status=status.HTTP_204_NO_CONTENT)
            
            if user_chat_room.is_active:
                user_chat_room.is_active = False
                user_chat_room.save()
                activity_notification.send(sender=self.__class__, type='Leave', chat_room=chat_room, user=user)

                # Trigger the custom signal for leaving the chat
                # user_chatroom_activity.send(sender=self.model, user=user, chat_room=chat_room, action='left')

                return Response({'success': 'Left the group chat successfully.'}, status=status.HTTP_200_OK)
            
            return Response({'error': 'User has already left the group.'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'detail': 'Joining and leaving chats restricted for groups only.'}, status=status.HTTP_400_BAD_REQUEST)
    
class UserChatRoomViewSet(ModelViewSet):
    """
    Provides a view for managing user chat rooms. This view allows authenticated users
    to perform CRUD operations on user chat rooms they are part of.
    
    The `update` method returns a 401 Unauthorized response if the user is not part of the chat room they are trying to update.
    
    The `destroy` method checks if the user is part of the chat room they are trying to delete.
    If the user is not part of the chat room, a 401 Unauthorized response is returned. Otherwise,
    the chat room is soft deleted.
    
    The `create` method creates two user chat room instances, one for each user participating in the chat room, within a transaction.
    The response includes the data for both user chat room instances.
    """
    queryset = UserChatRoom.objects.all()
    serializer_class = UserChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_context(self):
        # Add the request object to the context
        context = super().get_serializer_context()
        context['request'] = self.request
        print('context____________________', context, 'data', self.request.data)
        return context
    
    def create(self, request, *args, **kwargs):
        chat_room_id = request.data.get('chat_room')
        chat_room = ChatRoom.objects.filter(id=chat_room_id).first()
        user = request.data.get('user') or request.user
        
        
        user_chat_room = UserChatRoom.objects.filter(chat_room=chat_room, user=user).first()
        if user_chat_room:
            user_chat_room.is_active = True
            user_chat_room.save()
            serializer = self.serializer_class(data=user_chat_room)
            serializer.is_valid()
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        # Check for private chat room limit
        if chat_room and chat_room.room_type == 'private':
            users_count = chat_room.user_chats.count()
            if users_count >= 2:
                return Response({'error': "Private chat can only have 2 users"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Ensure 'name' is included in data
        data = request.data.copy()
        data['is_active'] = True
        serializer = self.serializer_class(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        # Create or update UserChatRoom instance
        user_chat = UserChatRoom.objects.filter(user=user, chat_room=chat_room).first()
        if user_chat:
            user_chat.is_active = True
            user_chat.save()
        else:
            self.perform_create(serializer)
            user_chat = serializer.instance

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.user == request.user:
            return Response({'error': 'Viewing other people\'s chat is not allowed'},
                            status=status.HTTP_403_FORBIDDEN)
        if not instance.is_active:
            return Response({'error': 'This chat was deleted.'})
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        user = request.user
        user_chats = UserChatRoom.objects.filter(user=user, is_active=True)
        serializer = self.serializer_class(user_chats, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def update(self, request, *args, **kwargs):
        if not self.get_object().user == request.user:
            return Response({'error': 'User must be part of the chatroom to be able to update it.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        if not self.get_object().is_active:
            return Response({'error': 'This chat was deleted.'})
        print('data________', request.data)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user != instance.user:
            return Response({'error': 'User must be part of the chatroom to be able to delete it.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'], url_path='status')
    def get_status(self, request, *args, **kwargs):
        instance = self.get_object()
        associated_user_chats = instance.chat_room.user_chats.filter(is_active=True)
        online_users = [c.user for c in associated_user_chats \
                        if c.user.profile.status == 'online' and c.user != request.user]
        if online_users:
            return Response({'status':'online'})
        return Response({'status':'offline'})



class MessageViewSet(ModelViewSet):
    """
    ViewSet for managing messages in a chat application.
    
    This ViewSet provides the following functionality:
    - Creating new messages in a chat room
    - Updating existing messages (if the user is the sender)
    - Deleting messages (if the user is the sender)
    - Listing messages is not allowed
    
    The ViewSet ensures that the user has the necessary permissions to perform the requested action, such as being a member of the chat room and not trying to access messages they don't have permission to view or modify.
    
    When a new message is created, the ViewSet also updates the last_sent_message field of the user's chat room, and if the chat room is a private chat, it sets the is_active flag to True for all user chat rooms associated with the chat room.
    
    The ViewSet also sends activity and message notifications when a new message is created.
    """
        
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        chat_room_id = request.data.get('chat_room')
        chat_room = ChatRoom.objects.filter(pk=chat_room_id).first()
        user = request.user

        if not chat_room:
            return Response({'error': 'Chatroom not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user_chat_room = chat_room.user_chats.filter(user=user).first()
        if not user_chat_room or not user_chat_room.is_active and user_chat_room.chat_room.room_type == 'group':
            return Response({'error': 'User doesn\'t have permission or chat doesn\'t exist.'},
                            status=status.HTTP_403_FORBIDDEN)
        
        content = request.data.get('content')
        attachment = request.data.get('attachment', None)

        try:
            # Ensure atomicity
            with transaction.atomic():
                # Create the message
                message = Message.objects.create(chat_room=chat_room, sender=user, content=content)
                user_chat_room.last_sent_message = message

                if chat_room.room_type == 'private':
                    # Update all user chat rooms for private chats
                    user_chat_rooms = chat_room.user_chats.all()
                    for chat in user_chat_rooms:
                        chat.is_active = True
                    UserChatRoom.objects.bulk_update(user_chat_rooms, ['is_active'])

        except IntegrityError as e:
            return Response({'error': f'Integrity error: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        user_chat_room.is_active = True
        user_chat_room.save()
        # If there is attachment data, create the attachment and associate it with the message
        if attachment:
            attachment_serializer = AttachmentSerializer(data=attachment)
            attachment_serializer.is_valid(raise_exception=True)
            attachment = attachment_serializer.save(message=message)
        # Serialize the message
        serializer = self.get_serializer(message)
        activity_notification.send(sender=self.__class__, type='Message', user=user, chat_room=chat_room)
        message_notification.send(sender=self.__class__, type='new_message', message=serializer.data, user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if instance.is_deleted:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'},
                            status=status.HTTP_400_BAD_REQUEST)
            
        if not instance.sender == user:
            return Response({'error': 'User can only edit their own messages.'},
                            status=status.HTTP_403_FORBIDDEN)
            
        partial = kwargs.pop('partial', False)
        data = request.data.copy()
        data['is_edited'] = True
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


    def list(self, request, *args, **kwargs):
        return Response({'detail': 'Listing messages not allowed.'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if instance.sender != user:
            return Response({'error': 'User can only delete their own messages.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        
        if instance.is_deleted:
            return Response({'error': 'Message is either deleted or not associated with this chatroom'},
                            status=status.HTTP_400_BAD_REQUEST)
        
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

        
class AttachmentViewSet(ModelViewSet):
    """
    Provides a ViewSet for managing file attachments associated with messages.
    
    The `AttachmentViewSet` class inherits from `ModelViewSet` and provides the following functionality:
    
    - `create`: Allows authenticated users to create a new attachment for a message they own. Handles base64-encoded file data.
    - `destroy`: Allows authenticated users to delete an attachment for a message they own.
    - `list`, `update`, and `retrieve`: Disallowed for this ViewSet.
    
    The `decode_base64_file` method is a helper function used to decode base64-encoded file data.
    """
        
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        message_id = request.data.get('message')
        message = Message.objects.filter(pk=message_id, sender=user).first()
        data = request.data.copy()
        if not message:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'},
                            status=status.HTTP_404_NOT_FOUND)
        
        if message.is_deleted:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        file_data = data.get('file')
        if isinstance(file_data, str):
            if file_data and file_data.startswith('data:'):
                # Handle base64 file
                file_data = self.decode_base64_file(file_data)
                data['file'] = file_data

        data['message'] = message_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def decode_base64_file(self, base64_data):
        """Decode base64 file and return a ContentFile."""
        try:
            format, base64_str = base64_data.split(';base64,')
            extension = format.split('/')[-1]
            file_data = base64.b64decode(base64_str)
            file_name = f'temp.{extension}'
            return ContentFile(file_data, file_name)
        except (ValueError, TypeError):
            raise ValueError("Invalid base64 file format")

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()

        if instance.message.sender != user:
            return Response({'error': 'User can only delete attachments from their own messages.'},
                            status=status.HTTP_403_FORBIDDEN)
        
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_403_FORBIDDEN)
    
    def retrieve(self, request, *args, **kwargs):
        return Response(status=status.HTTP_403_FORBIDDEN)


class ReactionViewSet(ModelViewSet):
    """
    ViewSet for handling Reaction model operations.
    
    Provides CRUD operations for Reactions, with the following functionality:
    
    - `create`: Creates a new Reaction for a given Message. Requires the user to be authenticated.
    - `list`: Retrieves a list of Reactions for a given Message.
    - `destroy`: Deletes a Reaction, but only if the Reaction was created by the current user.
    - `update`: Updates a Reaction, but only if the Reaction was created by the current user.
    - `retrieve`: Returns a 403 Forbidden response, as retrieving individual Reactions is not allowed.
    
    The ViewSet also ensures that the Message the Reaction is associated with has not been deleted.
    """
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        message_id = request.data.get('message')
        message = Message.objects.filter(pk=message_id, is_deleted=False).first()
        
        if not message:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'},
                            status=status.HTTP_404_NOT_FOUND)

        if message.is_deleted:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'}, 
                            status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['user'] = user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        activity_notification.send(sender=self.__class__, type='Reaction', chat_room=message.chat_room, reaction=serializer.data, user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        print(kwargs)
        message_id = request.query_params.get('message')  # Use query params for list

        message = Message.objects.filter(pk=message_id).first()
        if not message:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'},
                            status=status.HTTP_404_NOT_FOUND)

        if message.is_deleted:
            return Response({'error': 'This Message was deleted or doesn\'t exist.'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.queryset.filter(message=message)
        serializer = self.get_serializer(queryset, many=True)  # Use queryset directly
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if instance.user != user:
            return Response({'error': 'User can only remove his own reactions.'},
                            status=status.HTTP_403_FORBIDDEN)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if instance.user != user:
            return Response({'error': 'User can only update his own reactions.'},
                            status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)  # Correct update
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        return Response({'error': 'Method not allowed.'}, status=status.HTTP_403_FORBIDDEN)
    
    
class NotificationViewSet(ModelViewSet):
    queryset = Notification.objects.all()
    model = Notification
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = self.queryset.filter(user=user)
        serializer = self.get_serializer(queryset, many=True)  # Use queryset directly
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        
    
"=============================================end chat===================================================="
