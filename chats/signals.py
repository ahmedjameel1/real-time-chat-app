# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Message, ChatRoom, UserChatRoom

# @receiver(post_save, sender=Message)
# def handle_message_save(sender, instance, created, **kwargs):
#     if created:
#         user_group_chat = UserChatRoom.objects.filter(chat_room=instance.chat_room, chat_room__room_type='group', is_active=True).first()
#         user_private_chat = UserChatRoom.objects.filter(chat_room=instance.chat_room, chat_room__room_type='private').first()
#         print(user_group_chat, user_private_chat)
#         if user_private_chat:
#             if user_private_chat.is_open == False:
#                 user_private_chat.unread_count = user_private_chat.unread_count + 1
#                 user_private_chat.save()
#         else:
#             if user_group_chat.is_open == False:
#                 user_group_chat.unread_count = user_group_chat.unread_count + 1
#                 user_group_chat.save()
#     else:
#         pass

from django.dispatch import Signal

activity_notification = Signal()
message_notification = Signal()
