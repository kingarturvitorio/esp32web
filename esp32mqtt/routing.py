from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/esp32/status/', consumers.StatusConsumer.as_asgi()),
]