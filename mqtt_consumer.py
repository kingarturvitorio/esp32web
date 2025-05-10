# mqtt_consumer.py

import os
import django
import json
import threading
import redis
import paho.mqtt.client as mqtt
from django.utils import timezone
from asgiref.sync import async_to_sync
import logging
logger = logging.getLogger(__name__)
# --- 1) CONFIGURAÇÃO DO DJANGO ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from esp32mqtt.models import Dispositivo, Medicao
from channels_redis.core import RedisChannelLayer

# --- 2) DEPENDÊNCIAS INFLUXDB ---
from influxdb_client import InfluxDBClient, Point, WritePrecision

# Carrega variáveis de ambiente (você pode usar python-dotenv ou definir no seu shell)
INFLUX_URL    = "http://18.117.46.69"     # ex: https://meu-influx.aws.com
INFLUX_TOKEN  = "ibPbxd-wNhLzfZBjMAAxXUJ-Do2HZDQxWLaGC28I-csL2LdLlSjhUl_iE7s2DPDXAK6v2nT0i8OPnKfd_mjOCw=="   # token com permissão de escrita
INFLUX_ORG    = "artur"     # nome da sua organização
INFLUX_BUCKET = "artur_v2"  # nome do bucket

# Inicializa client Influx
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = influx_client.write_api()

# --- 3) CONFIGURAÇÃO REDIS / CHANNEL LAYER ---
redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
pubsub      = redis_client.pubsub()

channel_layer = RedisChannelLayer(hosts=[("127.0.0.1", 6379)])

# --- 4) FUNÇÃO PARA ESCUTAR COMANDOS via Redis ---
def redis_listener():
    pubsub.subscribe("comandos_esp32")
    print("📡 Escutando comandos no canal Redis 'comandos_esp32'…")
    for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        try:
            comando = json.loads(msg["data"].decode())
            print("🟨 Comando recebido:", comando)

            # Exemplo de aplicação do comando no MQTT
            identificador = comando.get("identificador")  # adapte se precisar
            if comando["comando"] == "setpoint":
                client.publish('setpoint', str(comando["valor"]))
            # ▶️ adicione outros comandos aqui…
        except Exception as e:
            print("❌ Erro ao processar comando no Redis:", e)

# --- 5) CALLBACKS MQTT ---
def on_connect(client, userdata, flags, rc):
    print("🟢 Conectado ao MQTT (rc=%s)" % rc)
    client.subscribe("esp32/#")  # escuta todos tópicos esp32/

def on_message(client, userdata, msg):
    try:
        parts = msg.topic.split('/')
        identificador = parts[1]
        tipo_dado     = parts[2]
        valor_str     = msg.payload.decode()
        timestamp     = timezone.now()

        # 5.1) ATUALIZAÇÃO no Django
        disp = Dispositivo.objects.get(identificador=identificador)
        disp.ultimo_ping = timestamp
        disp.save()

        try:
            valor_float = float(valor_str)
            Medicao.objects.create(
                dispositivo=disp,
                tipo=tipo_dado,
                valor=valor_float,
                timestamp=timestamp
            )
        except ValueError:
            # Se não for float, ignora criação de Medicao
            valor_float = None

        # 5.2) ESCREVE no InfluxDB (só se for numérico)
        if valor_float is not None:
            p = (
                Point("medicao")
                .tag("dispositivo", identificador)
                .tag("tipo", tipo_dado)
                .field("valor", valor_float)
                .time(timestamp, WritePrecision.NS)
            )
            try:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                print("→ Escrita InfluxDB:", p.to_line_protocol())
            except write_api.exceptions.ApiError as e:
                    if e.status == 404:
                        logger.error("Erro InfluxDB 404: verifique bucket/endereço")
                        # talvez só logar UMA vez, ou usar backoff/retry
                    else:
                        logger.exception("Erro InfluxDB inesperado")


        # 5.3) ENVIA via Channels → WebSocket
        async_to_sync(channel_layer.group_send)(
            "esp32_status",
            {
                "type": "send_status",
                "data": {
                    "identificador": identificador,
                    "tipo": tipo_dado,
                    "valor": valor_str,
                    "status": "online",
                    "timestamp": timestamp.isoformat()
                }
            }
        )
        print(f"📡 Publicado WS e Influx: {identificador} | {tipo_dado} = {valor_str}")

    except Exception as e:
        print("❌ Erro no on_message:", e)

# --- 6) CONFIGURA E INICIA MQTT CLIENT ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
client.on_connect = on_connect
client.on_message = on_message

# conecte ao broker (pode ser localhost ou IP AWS)
client.connect("18.117.46.69", 1883, 60)

# Inicia thread para comandos Redis
threading.Thread(target=redis_listener, daemon=True).start()

print("🔄 Aguardando mensagens MQTT…")
client.loop_forever()
