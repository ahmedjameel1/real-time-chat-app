from rest_framework import serializers
from chats.models import ChatRoom, UserChatRoom, Message, Attachment, Reaction, Notification


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Attachment model."""
    class Meta:
        model = Attachment
        fields = '__all__'

class ReactionSerializer(serializers.ModelSerializer):
    """Serializer for Reaction model."""
    class Meta:
        model = Reaction
        fields = ['id', 'message', 'user', 'reaction_type', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            if request.method == 'POST':
                self.fields['message'].required = True
                self.fields['reaction_type'].required = True
            elif request.method in ['PUT', 'PATCH']:
                self.fields['user'].read_only = True
                self.fields['message'].read_only = True


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    attachment = AttachmentSerializer(read_only=True, required=False, allow_null=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    sender_full_name = serializers.SerializerMethodField()
    formatted_timestamp = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender_full_name', 'chat_room', 'sender', 'content', 'is_edited', 'reactions', 'attachment', 'formatted_timestamp']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            if request.method == 'POST':
                self.fields['chat_room'].required = True
                self.fields['content'].required = True
            elif request.method in ['PUT', 'PATCH']:
                self.fields['chat_room'].read_only = True

    def get_sender_full_name(self, obj):
        return obj.sender.first_name + ' ' + obj.sender.last_name
    
    def get_formatted_timestamp(self, obj):
        """Format timestamp as 'Month Day, Year - hour:minute AM/PM'."""
        timestamp = obj.timestamp
        return timestamp.strftime('%B %d, %Y - %I:%M %p') if timestamp else None
        
    
class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for ChatRoom model."""
    class Meta:
        model = ChatRoom
        fields = ['id', 'room_type', 'created_at', 'updated_at']

class UserChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for UserChatRoom model."""
    new_messages = MessageSerializer(many=True, read_only=True)
    room_type = serializers.SerializerMethodField()
    last_sent_message = MessageSerializer(required=False, read_only=True)
    last_seen_message = MessageSerializer(required=False, read_only=True)


    class Meta:
        model = UserChatRoom
        fields = ['id', 'name', 'user', 'chat_room', 'room_type', 'joined_at', 'is_active',
                  'new_messages', 'last_sent_message', 'last_seen_message',
                  'is_read']

    def get_room_type(self, obj):
        """Get the room type from the associated ChatRoom."""
        return obj.chat_room.room_type

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    message = MessageSerializer(read_only=True)
    reaction = ReactionSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'message', 'body', 'reaction', 'user', 'chat_room']

    