import os, django, redis
from channels_redis.core import RedisChannelLayer
from asgiref.sync import async_to_sync

# --- configura Django ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# --- channel layer (Channels) ---
channel_layer = RedisChannelLayer(hosts=[("127.0.0.1", 6379)])

# --- cliente Redis para pub/sub de comandos ---
redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
