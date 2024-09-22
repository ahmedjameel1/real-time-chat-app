from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'chat_rooms', views.ChatRoomViewSet, basename='chat-rooms')
router.register(r'user_chats', views.UserChatRoomViewSet, basename='user-chats')
router.register(r'messages', views.MessageViewSet, basename='messages')
router.register(r'attachments', views.AttachmentViewSet, basename='attachments')
router.register(r'reactions', views.ReactionViewSet, basename='reactions')
router.register(r'notifications', views.NotificationViewSet, basename='notifications')
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'e2ee_keys', views.E2EEKeyViewSet, basename='e2ee-keys')

urlpatterns = [
    path('auth/token/', views.EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls
