import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()
from channels.routing import ProtocolTypeRouter, URLRouter

import django
from channels.auth import AuthMiddlewareStack



import esp32mqtt.routing


django.setup()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            esp32mqtt.routing.websocket_urlpatterns
        )
    ),
})
