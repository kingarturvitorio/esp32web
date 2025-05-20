import json, redis
from django.conf import settings

redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)

def enviar_comando_open_lock(identificador):
    payload = {
        "identificador": identificador,
        "comando":       "open_lock"
    }
    redis_client.publish("comandos_esp32", json.dumps(payload))
