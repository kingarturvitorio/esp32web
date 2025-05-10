import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter

import django
from channels.auth import AuthMiddlewareStack



import esp32mqtt.routing


django.setup()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = ProtocolTypeRouter({
    # qualquer requisição HTTP vai para o Django normal
    "http": get_asgi_application(),

    # só as websockets são roteadas por Channels
    "websocket": URLRouter(
        esp32mqtt.routing.websocket_urlpatterns
    ),
})