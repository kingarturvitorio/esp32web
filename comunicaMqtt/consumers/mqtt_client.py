import paho.mqtt.client as mqtt
from .handlers import handle_mqtt_message
from .base import redis_client
from .redis_listener import start_redis_listener

def on_connect(client, userdata, flags, rc):
    print("🟢 Conectado ao broker MQTT (rc=", rc, ")")
    client.subscribe("esp32/#")

def on_message(client, userdata, msg):
    try:
        handle_mqtt_message(msg.topic, msg.payload)
        print(f"📡 Mensagem processada: {msg.topic} -> {msg.payload}")
    except Exception as e:
        print("Erro no handler MQTT:", e)

def run_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("18.117.46.69", 1883, 60)

    # inicia listener Redis em thread
    start_redis_listener(client)

    print("🔄 Aguardando mensagens MQTT...")
    client.loop_forever()
