# mqtt_consumer.py

import os
import django
import json
import paho.mqtt.client as mqtt
from django.utils import timezone
# Configuração do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')  # Altere para o nome do seu projeto
django.setup()
import redis
import threading

# Importar os modelos
from esp32mqtt.models import Dispositivo, Medicao

from channels_redis.core import RedisChannelLayer

# Configure manualmente a conexão Redis (sem depender de settings.py)
channel_layer = RedisChannelLayer(
    hosts=[("127.0.0.1", 6379)]  # ou altere a porta se necessário
)

print("🔧 Canal configurado:", channel_layer)
from asgiref.sync import async_to_sync

# Redis pub/sub para comandos
redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
pubsub = redis_client.pubsub()

def redis_listener():
    pubsub.subscribe("comandos_esp32")
    print("📡 Escutando comandos no canal Redis 'comandos_esp32'...")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                comando = json.loads(message["data"].decode())
                print("🟨 Comando recebido via Redis:", comando)

                id_esp = 'c8f09eec0e78'
                if not id_esp:
                    print("⚠️ Comando ignorado — identificador ausente")
                    continue

                if comando["comando"] == "setpoint":
                    valor = comando["valor"]
                    
                    client.publish(f'setpoint', str(valor))
                    print(valor)

                elif comando["comando"] == "motor":
                    motor = comando["motor"]
                    acao = comando["acao"]
                    client.publish(f"esp32/{id_esp}/atuadores/{motor}", acao)

            except Exception as e:
                print("❌ Erro ao processar comando do Redis:", e)


def on_connect(client, userdata, flags, rc):
    print("🟢 Conectado ao MQTT Broker com código:", rc)
    client.subscribe("esp32/#")  # Exemplo: esp32/123ABC/dados

def on_message(client, userdata, msg):
    try:
        parts = msg.topic.split('/')
        print(parts)
        identificador = parts[1]
        tipo_dado = parts[2] #ex temperature, umidade_ambiente, etc.

        valor = msg.payload.decode()

        # Atualiza dispositivo no banco
        dispositivo = Dispositivo.objects.get(identificador=identificador)
        dispositivo.ultimo_ping = timezone.now()
        dispositivo.save()

        try:
            valor_float = float(valor)
            Medicao.objects.create(
                dispositivo=dispositivo,
                tipo=tipo_dado,
                valor=valor_float
            )
        except ValueError:
            pass  # Ignora se não for número (ex: status textual ou comando)
                
        # Envia status via WebSocket
        async_to_sync(channel_layer.group_send)(
            "esp32_status",
            {
                "type": "send_status",
                "data": {
                    "identificador": identificador,
                    "tipo": tipo_dado,
                    "valor": valor,
                    "status": "online",
                    "timestamp": timezone.now().isoformat()
                }
            }
        )
        print("Enviando dados")
        print(f"📡 Enviado: {identificador} | {tipo_dado} = {valor}")
    except Exception as e:
        print("Erro ao processar mensagem:", e)

# --- Conectar ao broker MQTT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message


# Conecta ao Mosquitto (ajuste IP se não for localhost)
client.connect("18.117.46.69", 1883, 60)

# Inicia thread separada para escutar comandos do Redis
threading.Thread(target=redis_listener, daemon=True).start()

print("🔄 Aguardando mensagens MQTT...")
client.loop_forever()
