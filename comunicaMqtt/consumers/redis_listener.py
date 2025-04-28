import threading
from .base import redis_client
from .handlers import handle_redis_command

def _listen(mqtt_client):
    pubsub = redis_client.pubsub()
    pubsub.subscribe("comandos_esp32")
    print("📡 Escutando canal Redis 'comandos_esp32'…")
    for msg in pubsub.listen():
        if msg['type'] == 'message':
            try:
                handle_redis_command(msg['data'], mqtt_client)
                print("🟨 Comando Redis enviado ao MQTT:", msg['data'])
            except Exception as e:
                print("Erro no listener Redis:", e)

def start_redis_listener(mqtt_client):
    thread = threading.Thread(target=_listen, args=(mqtt_client,), daemon=True)
    thread.start()
