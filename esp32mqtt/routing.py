from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path(r'ws/esp32/status/', consumers.StatusConsumer.as_asgi()),
]