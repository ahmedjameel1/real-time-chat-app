from django.urls import path

from .consumers import GeneralUpdatesConsumers, UserStatusConsumers

websocket_urlpatterns = [
    path("ws/general_updates/", GeneralUpdatesConsumers.GeneralUpdatesConsumer.as_asgi()),
    path('ws/user_status/', UserStatusConsumers.UserStatusConsumer.as_asgi()),
]