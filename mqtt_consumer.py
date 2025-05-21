# mqtt_consumer.py

import os
import django
import json
import threading
import redis
import paho.mqtt.client as mqtt
from django.utils import timezone
from asgiref.sync import async_to_sync
import logging.config
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.conf import settings
# carrega o dict LOGGING do settings.py
logging.config.dictConfig(settings.LOGGING)
import logging
logger = logging.getLogger('mqtt_consumer')
# --- 1) CONFIGURAÇÃO DO DJANGO ---
from influxdb_client.rest import ApiException

from esp32mqtt.models import Dispositivo, Medicao
from controle_acesso.models import Cartao, EventoAcesso
from channels_redis.core import RedisChannelLayer

# --- 2) DEPENDÊNCIAS INFLUXDB ---
from influxdb_client import InfluxDBClient, Point, WritePrecision

# Carrega variáveis de ambiente (você pode usar python-dotenv ou definir no seu shell)
INFLUX_URL    = "http://18.117.46.69:8086"     # ex: https://meu-influx.aws.com
INFLUX_TOKEN  = "ibPbxd-wNhLzfZBjMAAxXUJ-Do2HZDQxWLaGC28I-csL2LdLlSjhUl_iE7s2DPDXAK6v2nT0i8OPnKfd_mjOCw=="   # token com permissão de escrita
INFLUX_ORG    = "artur"     # nome da sua organização
INFLUX_BUCKET = "artur_v3"  # nome do bucket

# Inicializa client Influx
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = influx_client.write_api()

# --- 3) CONFIGURAÇÃO REDIS / CHANNEL LAYER ---

# --- 3) CONFIGURAÇÃO REDIS / CHANNEL LAYER ---
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)
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
    
    topic = msg.topic
    # 0) Ignore suas próprias respostas:
    if topic.endswith("/rfid/resp"):
        return
    
    print(f"💬 Mensagem recebida no MQTT — tópico: {msg.topic}, payload: {msg.payload}")
    
    
    try:   
        parts         = msg.topic.split('/')
        identificador = parts[1]
        tipo_dado     = parts[2]
        payload       = msg.payload.decode()
        timestamp     = timezone.now()

        # 1) Atualiza ping do dispositivo
        disp = Dispositivo.objects.get(identificador=identificador)
        disp.ultimo_ping = timestamp
        disp.save()

        if tipo_dado == 'rfid':
            # ── lida com RFID ──
            uid = payload
            try:
                # já traz o usuario para não fazer outra query depois
                cartao = Cartao.objects.select_related('usuario').get(uid=uid, ativo=True)
                usuario = cartao.usuario
                # você pode verificar is_active ou uma permissão específica aqui
                autorizado = usuario.is_active
            except Cartao.DoesNotExist:
                cartao     = None
                usuario    = None
                autorizado = False

            EventoAcesso.objects.create(
                cartao      = cartao,
                dispositivo = identificador,
                autorizado  = autorizado
            )

            # Resposta ao ESP32
            topic_cmd = f'esp32/{identificador}/atuadores/2'
            payload_cmd = "on" if autorizado else "off"
            client.publish(topic_cmd, payload_cmd)

        else:
            # ── lida com sensores numéricos ──
            try:
                valor_float = float(payload)

                # 2.1) grava no Django
                Medicao.objects.create(
                    dispositivo=disp,
                    tipo       = tipo_dado,
                    valor      = valor_float,
                    timestamp  = timestamp
                )

                # 2.2) envia para o InfluxDB
                p = (
                    Point("medicao")
                    .tag("dispositivo", identificador)
                    .tag("tipo",        tipo_dado)
                    .field("valor",      valor_float)
                    .time(timestamp, WritePrecision.NS)
                )
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
            except ApiException as e:
                print("⚠️ Erro ao escrever no InfluxDB:")
                print(e.body)  # Isso mostra o corpo HTML de erro detalhado

            except ValueError:
                # não era número, ignora
                pass

        # 3) broadcast via Channels (usa async_to_sync)
        async_to_sync(channel_layer.group_send)(
            "esp32_status",
            {
                "type": "send_status",
                "data": {
                    "identificador": identificador,
                    "tipo":          tipo_dado,
                    "valor":         payload,
                    "timestamp":     timestamp.isoformat()
                }
            }
        )

    except Exception:
        logger.exception("Erro no on_message")

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
